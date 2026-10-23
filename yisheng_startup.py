# -*- coding: utf-8 -*-
"""YishengTranslator minimal first-run environment bootstrap (Windows)."""
from __future__ import annotations

import hashlib
import importlib.metadata
import os
from pathlib import Path
import re
import subprocess
import sys
import traceback

ENV_CHILD = "YISHENG_AUTO_ENV_CHILD"
DELEGATED = "YISHENG_PYW_DELEGATED"
# Keep this list data-only; pip reads the full validated project requirements file.
_REQ = re.compile(r"^([A-Za-z0-9_.-]+)\s*(.*)$")
_SPEC = re.compile(r"^(>=|<=|==|>|<)\s*([0-9]+(?:\.[0-9]+)*)$")


class SetupError(RuntimeError):
    pass


def _version_tuple(value: str) -> tuple[int, ...]:
    parts = re.match(r"^\s*(\d+(?:\.\d+)*)", value)
    if parts is None:
        return ()
    return tuple(int(n) for n in parts.group(1).split("."))


def _compare_version(installed: str, op: str, required: str) -> bool:
    a, b = _version_tuple(installed), _version_tuple(required)
    if not a or not b:
        return False
    width = max(len(a), len(b))
    a += (0,) * (width - len(a))
    b += (0,) * (width - len(b))
    return {">=": a >= b, "<=": a <= b, "==": a == b,
            ">": a > b, "<": a < b}[op]


def _requirements(path: Path) -> list[tuple[str, list[tuple[str, str]]]]:
    if not path.is_file():
        raise SetupError("缺少 requirements.txt，请复制完整程序目录。")
    result = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.partition("#")[0].strip()
        if not line:
            continue
        match = _REQ.fullmatch(line)
        if match is None:
            raise SetupError("不支持的依赖格式：" + line)
        name, constraints = match.groups()
        specs = []
        if constraints:
            for token in constraints.split(","):
                spec = _SPEC.fullmatch(token.strip())
                if spec is None:
                    raise SetupError("不支持的依赖版本约束：" + line)
                specs.append((spec.group(1), spec.group(2)))
        result.append((name, specs))
    if not result:
        raise SetupError("requirements.txt 为空。")
    return result


def _dependencies_ok(requirements: Path) -> bool:
    for name, constraints in _requirements(requirements):
        try:
            installed = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            return False
        if not all(_compare_version(installed, op, ver) for op, ver in constraints):
            return False
    return True


def _notify(message: str, title: str = "译声实时翻译") -> None:
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, title, 0x40)
    except (AttributeError, OSError):
        print(title + ": " + message, file=sys.stderr)


def _python_console() -> Path:
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe":
        sibling = exe.with_name("python.exe")
        if sibling.is_file():
            return sibling
    return exe


def _environment_dir(root: Path) -> Path:
    user_home = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    root_key = hashlib.sha256(str(root.resolve()).casefold().encode("utf-8")).hexdigest()[:12]
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    return user_home / "YishengTranslator" / "envs" / f"{version}-{root_key}"


def _run_command(command: list[str], log: Path, timeout: int) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as stream:
        stream.write("Running: " + str(Path(command[0]).name) + " " +
                     " ".join(command[1:3]) + "\n")
        stream.flush()
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, check=False, timeout=timeout,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode != 0:
        raise SetupError(f"环境安装失败（退出代码 {result.returncode}）。详情见：{log}")


def _environment_ok(python: Path, requirements: Path, root: Path) -> bool:
    """Check that a cached environment still satisfies the project's requirements."""
    if not python.is_file():
        return False
    probe = ("import sys; from pathlib import Path; "
             "sys.path.insert(0, sys.argv[1]); "
             "from yisheng_startup import _dependencies_ok; "
             "sys.exit(0 if _dependencies_ok(Path(sys.argv[2])) else 1)")
    try:
        result = subprocess.run([str(python), "-B", "-c", probe, str(root), str(requirements)],
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, check=False, timeout=15,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _prepare_environment(root: Path) -> Path | None:
    requirements = root / "requirements.txt"
    _requirements(requirements)
    # Reuse an existing working project environment before creating a second one.
    # A Windows .pyw file can start under a different registered Python executable.
    local_python = root / ".venv" / "Scripts" / "python.exe"
    if _environment_ok(local_python, requirements, root):
        if local_python.parent.resolve() == Path(sys.executable).resolve().parent:
            return None
        local_pythonw = local_python.with_name("pythonw.exe")
        return local_pythonw if local_pythonw.is_file() else local_python
    # Otherwise keep a working current interpreter unchanged.
    if _dependencies_ok(requirements):
        return None
    env_root = _environment_dir(root)
    python = env_root / "Scripts" / "python.exe"
    pythonw = env_root / "Scripts" / "pythonw.exe"
    log = env_root.parent / "bootstrap.log"
    stamp = env_root / ".yisheng-requirements"
    fingerprint = hashlib.sha256(requirements.read_bytes()).hexdigest()
    config = env_root / "pyvenv.cfg"
    original_home = ""
    if config.is_file():
        for line in config.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("home ="):
                original_home = line.partition("=")[2].strip().casefold()
    base_executable = Path(getattr(sys, "_base_executable", sys.executable)).resolve()
    healthy_home = not config.exists() or original_home == str(base_executable.parent).casefold()
    # Refuse to modify an environment that appears to belong to another machine.
    if not healthy_home and env_root.exists():
        raise SetupError("检测到迁移后失效的 Python 环境，请删除该目录后重新启动：" + str(env_root))
    if not python.is_file():
        _run_command([str(_python_console()), "-m", "venv", str(env_root)], log, 120)
    if not python.is_file():
        raise SetupError("无法创建 Python 虚拟环境：" + str(env_root))
    if (not stamp.is_file() or stamp.read_text(encoding="ascii", errors="ignore") != fingerprint
            or not _environment_ok(python, requirements, root)):
        _notify("首次启动需要在个人目录配置 Python 依赖。点击确定后自动安装，详细进度记录在 bootstrap.log。")
        _run_command([str(python), "-m", "pip", "install", "--disable-pip-version-check",
                      "-r", str(requirements)], log, 1800)
        if not _environment_ok(python, requirements, root):
            raise SetupError("依赖安装结束，但验证仍未通过。详情见：" + str(log))
        stamp.write_text(fingerprint, encoding="ascii")
    return pythonw if pythonw.is_file() else python


def _resource_warnings(root: Path) -> list[str]:
    missing = []
    resources = (
        ("界面资源", [root / "jpsub/assets/icon.png", root / "work/embedded-assets/icon.png"]),
        ("日语识别模型", [root / "models/parakeet-ja-0.6b-int8/model.int8.onnx"]),
        ("识别 tokens", [root / "models/parakeet-ja-0.6b-int8/tokens.txt"]),
        ("VAD 模型", [root / "models/silero_vad.onnx"]),
        ("本地翻译模型", [root / "models/llm/Hy-MT2-7B-Q4_K_M.gguf"]),
        ("CPU 翻译引擎", [root / "engine/cpu/llama-server.exe"]),
    )
    for label, choices in resources:
        if not any(p.is_file() and p.stat().st_size > 0 for p in choices):
            missing.append(label)
    return missing


def prepare(root: Path, entry: Path, args: list[str]) -> bool:
    """Return True if a prepared subprocess was started; False to run in-process."""
    if os.environ.get(ENV_CHILD) == "1":
        return False
    if sys.platform != "win32" or sys.version_info < (3, 11) or sys.maxsize <= 2**32:
        raise SetupError("需要 Windows x64 和 Python 3.11 或更高版本。")
    if not (root / "YishengTranslator_memory_limit.pyw").is_file():
        raise SetupError("主程序缺失，请复制完整程序文件夹。")
    try:
        interpreter = _prepare_environment(root)
        warnings = _resource_warnings(root)
        if warnings:
            _notify("以下程序资源尚未齐全：\n- " + "\n- ".join(warnings) +
                    "\n\n请复制原电脑的 models/、engine/、jpsub/assets/，"
                    "或在程序设置中下载缺失模型。不会擅自下载大型文件。")
        if not interpreter:
            return False
        env = os.environ.copy()
        env[ENV_CHILD] = "1"
        env[DELEGATED] = "1"
        subprocess.Popen([str(interpreter), "-B", str(entry), *args], cwd=str(root),
                         env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return True
    except (OSError, subprocess.TimeoutExpired, SetupError) as exc:
        detail = str(exc)
        _notify(detail, "译声环境配置失败")
        raise SetupError(detail) from exc
