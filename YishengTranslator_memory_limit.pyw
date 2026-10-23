# -*- coding: utf-8 -*-
# 译声实时翻译：可阅读、按原始模块分区的单文件 Python 程序
# 下面每个 BEGIN MODULE 对应一个完整源码文件，代码直接可见、可搜索。
# Python 一个 .pyw 只有一个原生模块。为了让相对导入和各模块全局变量仍能
# 互相隔离，下方用最小的导入加载器，从本文件的可读区块恢复原模块作用域。
# 不再将源码编码、压缩或放进字符串。图片/模型/依赖仍使用外部资源目录。
from __future__ import annotations
import hashlib
import importlib.abc
import linecache
import importlib.util
import os
import re
import subprocess
import sys
import textwrap
import traceback
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
os.chdir(_ROOT)
for _name in ("runtime/packages", ".venv/Lib/site-packages"):
    _folder = _ROOT / _name
    if _folder.is_dir() and str(_folder) not in sys.path:
        sys.path.append(str(_folder))

_MODULE_INDEX = {'jpsub': ('jpsub/__init__.py', True), 'jpsub.core': ('jpsub/core/__init__.py', True), 'jpsub.core.asr': ('jpsub/core/asr.py', False), 'jpsub.core.audio': ('jpsub/core/audio.py', False), 'jpsub.core.config': ('jpsub/core/config.py', False), 'jpsub.core.http_util': ('jpsub/core/http_util.py', False), 'jpsub.core.llama_engine': ('jpsub/core/llama_engine.py', False), 'jpsub.core.model_catalog': ('jpsub/core/model_catalog.py', False), 'jpsub.core.pipeline': ('jpsub/core/pipeline.py', False), 'jpsub.core.segment': ('jpsub/core/segment.py', False), 'jpsub.core.translate': ('jpsub/core/translate.py', False), 'jpsub.main': ('jpsub/main.py', False), 'jpsub.paths': ('jpsub/paths.py', False), 'jpsub.ui': ('jpsub/ui/__init__.py', True), 'jpsub.ui.background': ('jpsub/ui/background.py', False), 'jpsub.ui.overlay': ('jpsub/ui/overlay.py', False), 'jpsub.ui.settings': ('jpsub/ui/settings.py', False), 'jpsub.ui.theme': ('jpsub/ui/theme.py', False), 'jpsub.ui.transcript': ('jpsub/ui/transcript.py', False), 'jpsub.ui.window': ('jpsub/ui/window.py', False)}
_ASSET_HASHES = {'backgrounds/01-shinjuku-neon.jpg': '5b1f086f6ba7afffd6439b03268227929941423c58688b643de7bbe9b9713128', 'backgrounds/02-shibuya-aerial.jpg': 'd5b085616668b4d792c9a6198e76112c8ce39b8eb1e0f9d233b4c5eb94fea333', 'backgrounds/03-fuji-chureito.jpg': '5ac7bfad50b986cef672631f855bc4d01aa69a4727e5f43898b6bffee2ee304c', 'backgrounds/04-fushimi-torii.jpg': '58287f63c1e2289b450a06d9b1ec669a7007018f7b3513ac21b2fc07b52f6b67', 'backgrounds/05-arashiyama-bamboo.jpg': 'c9457819c417a96e3a0a2c3e2b418ad4c8fa94645b365036da7822046c9437c6', 'backgrounds/06-tokyo-street.jpg': 'f61fcbf305da46fd241030fe9cc27bb036f970e5bbde83d12e9a9184983d3594', 'backgrounds/07-sakura.jpg': 'fe8dfc982cd0c2f7fef31114e2b208eec18fca25960aee4d31f82617611c0d22', 'backgrounds/08-kabukicho.jpg': 'ef7bc1e07b18151704c1da69e8213ec370e804d763c034d9b619c1e0816791ac', 'backgrounds/credits.json': '91df662f9b437d97ac4e1ba65b2c3dbcc3681d80b2d7bf2f10a646d5c3a17180', 'check.png': '8ad00051e62f60e50062f83a7e002ab5a319b71a8138081c6fc8dbecf676548e', 'icon.ico': '88c6ba4be72ad4e44284f7ce9d2b49e118fcd6ae44b1c0647df9a6499f9a3f9f', 'icon.png': '2fde982f95efb11bd9413e5c49eecd240dfb933cc2281b8408e96536c04507e6'}
_MODULE_SOURCES = None

def _read_module_source(module_name):
    """从本 .pyw 可读区块加载源码；按标记检索，手工添加代码行也不会破坏索引。"""
    global _MODULE_SOURCES
    if _MODULE_SOURCES is None:
        blocks = {}
        active_name = None
        collecting = False
        current_lines = []
        for line in Path(__file__).read_text(encoding="utf-8").splitlines(True):
            if line.startswith("# BEGIN MODULE: "):
                if active_name is not None:
                    raise RuntimeError("源码分区缺少结尾：" + active_name)
                active_name = line[len("# BEGIN MODULE: "):].split("  (", 1)[0]
                if active_name not in _MODULE_INDEX or active_name in blocks:
                    raise RuntimeError("源码分区未登记或重复：" + active_name)
                collecting = False
                current_lines = []
            elif active_name is not None:
                if line.startswith("# END MODULE: "):
                    if line.strip() != "# END MODULE: " + active_name or not collecting:
                        raise RuntimeError("源码分区结束标记错误：" + active_name)
                    code = textwrap.dedent("".join(current_lines))
                    # Python 的 future import 不允许放在 if False 内，编译前恢复。
                    code = re.sub(r"(?m)^# __FUTURE_IMPORT__ (from __future__ import .+)$",
                                  r"\1", code)
                    # 展示用空模块的 pass 不是原文件业务代码。
                    code = re.sub(r"(?m)^pass  # __DISPLAY_ONLY__\n?", "", code)
                    blocks[active_name] = code
                    active_name = None
                elif line.startswith("if False:  # 可阅读的源码区块"):
                    collecting = True
                elif collecting:
                    current_lines.append(line)
        if active_name is not None or set(blocks) != set(_MODULE_INDEX):
            raise RuntimeError("单文件模块区块缺失或不完整")
        _MODULE_SOURCES = blocks
    return _MODULE_SOURCES[module_name]

class _ReadableModuleLoader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, fullname, path=None, target=None):
        record = _MODULE_INDEX.get(fullname)
        if record is None:
            return None
        relative, is_package = record
        spec = importlib.util.spec_from_loader(
            fullname, self, origin=str(_ROOT / relative), is_package=is_package)
        if is_package:
            spec.submodule_search_locations = [str((_ROOT / relative).parent)]
        return spec

    def create_module(self, spec):
        return None

    def get_source(self, fullname):
        if fullname not in _MODULE_INDEX:
            raise ImportError(fullname)
        return _read_module_source(fullname)

    def exec_module(self, module):
        relative, is_package = _MODULE_INDEX[module.__name__]
        location = str(_ROOT / relative)
        module.__file__ = location
        if is_package:
            module.__path__ = [str((_ROOT / relative).parent)]
        source = _read_module_source(module.__name__)
        # Source lives in this .pyw rather than virtual jpsub/*.py paths.
        # linecache makes Python tracebacks and inspect.getsource work.
        linecache.cache[location] = (
            len(source), None, source.splitlines(keepends=True), location)
        exec(compile(source, location, "exec", dont_inherit=True), module.__dict__)
        if module.__name__ == "jpsub.paths":
            # 资源保留为正常图片文件，而不是藏进巨大的 base85 字符串。
            assets = _ROOT / "work/embedded-assets"
            if not (assets / "icon.png").is_file():
                assets = _ROOT / "jpsub/assets"
            module.ASSETS = assets
            module.BACKGROUNDS = assets / "backgrounds"

sys.meta_path.insert(0, _ReadableModuleLoader())

def _delegate():
    if os.environ.get("YISHENG_PYW_DELEGATED") == "1":
        return False
    current = Path(sys.executable).resolve()
    for candidate in (_ROOT / ".venv/Scripts/pythonw.exe",
                      _ROOT / "runtime/pythonw.exe",
                      _ROOT / "runtime/python/pythonw.exe"):
        if not candidate.is_file():
            continue
        target = candidate.resolve()
        if target == current or target.parent == current.parent:
            return False
        env = os.environ.copy()
        env["YISHENG_PYW_DELEGATED"] = "1"
        subprocess.Popen([str(target), "-B", str(Path(__file__).resolve()),
                          *sys.argv[1:]], cwd=str(_ROOT), env=env,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return True
    return False

def _main():
    if "--bundle-check" in sys.argv:
        for name in _MODULE_INDEX:
            relative = _MODULE_INDEX[name][0]
            compile(_read_module_source(name), str(_ROOT / relative),
                    "exec", dont_inherit=True)
        assets = _ROOT / "work/embedded-assets"
        if not assets.is_dir():
            assets = _ROOT / "jpsub/assets"
        for name, expected_hash in _ASSET_HASHES.items():
            path = assets / name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
                raise RuntimeError("外部界面资源丢失或损坏：" + str(path))
        # A syntax check alone missed obsolete modules with broken imports.
        # Validate every shipped runtime module can actually be imported.
        import importlib
        for name in _MODULE_INDEX:
            importlib.import_module(name)
        print("BUNDLE_OK modules", len(_MODULE_INDEX), "assets", len(_ASSET_HASHES),
              "format READABLE IMPORT_OK")
        return 0
    if "--selftest" not in sys.argv:
        from yisheng_startup import prepare
        if prepare(_ROOT, Path(__file__).resolve(), sys.argv[1:]):
            return 0
        # Current interpreter passed dependency check; do not select a copied .venv.
        os.environ["YISHENG_PYW_DELEGATED"] = "1"
    if _delegate():
        return 0
    from jpsub.main import _run
    return _run()

def _report():
    details = traceback.format_exc()
    path = _ROOT / "single-pyw-error.log"
    try:
        with path.open("a", encoding="utf-8") as file:
            file.write(details + "\n")
    except OSError:
        pass
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            None, "程序启动失败，详细错误见：" + str(path),
            "译声实时翻译 - 启动错误", 0x10)
    except Exception:
        pass

if __name__ == "__main__":
    try:
        raise SystemExit(_main())
    except SystemExit:
        raise
    except BaseException:
        _report()
        raise

# =====================================================================
# 以下全部是普通 Python 源码，按模块分区，搜索函数名或类名即可定位。
# if False 只是不让这些定义提前在主文件全局作用域运行；
# 模块导入时，由上方加载器按行读取该区块到独立的原模块命名空间。
# =====================================================================

# ======================================================================
# BEGIN MODULE: jpsub  (jpsub/__init__.py)
# ======================================================================
if False:  # 可阅读的源码区块（独立模块由上方加载器执行）
    # -*- coding: utf-8 -*-
    """JPTran - 译声实时翻译（本地识别 + 云端/本地翻译）。"""

    __version__ = "0.9.6"
    APP_NAME = "译声实时翻译"
# END MODULE: jpsub

# ======================================================================
# BEGIN MODULE: jpsub.core  (jpsub/core/__init__.py)
# ======================================================================
if False:  # 可阅读的源码区块（独立模块由上方加载器执行）
    # -*- coding: utf-8 -*-
    pass  # __DISPLAY_ONLY__
# END MODULE: jpsub.core

# ======================================================================
# BEGIN MODULE: jpsub.core.asr  (jpsub/core/asr.py)
# ======================================================================
if False:  # 可阅读的源码区块（独立模块由上方加载器执行）
    # -*- coding: utf-8 -*-
    """唯一的日语语音识别引擎：Parakeet 0.6B INT8。"""
    # __FUTURE_IMPORT__ from __future__ import annotations

    import threading
    import time
    import wave
    from dataclasses import dataclass
    from pathlib import Path

    import numpy as np

    from ..paths import MODELS
    from .audio import normalize_gain


    MODEL_DIR = MODELS / "parakeet-ja-0.6b-int8"


    @dataclass
    class AsrResult:
        text: str
        seconds: float
        audio_seconds: float

        @property
        def rtf(self) -> float:
            return self.seconds / self.audio_seconds if self.audio_seconds > 0 else 0.0


    class _Parakeet:
        def __init__(self, num_threads: int):
            self.num_threads = num_threads
            self._recognizer = None

        def load(self) -> None:
            if self._recognizer is not None:
                return
            import sherpa_onnx

            model = MODEL_DIR / "model.int8.onnx"
            tokens = MODEL_DIR / "tokens.txt"
            if not (model.is_file() and tokens.is_file()):
                raise FileNotFoundError("日语识别模型不完整，请重新安装软件")
            self._recognizer = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(
                model=str(model), tokens=str(tokens), num_threads=self.num_threads,
            )

        def transcribe(self, samples: np.ndarray) -> AsrResult:
            self.load()
            started = time.perf_counter()
            stream = self._recognizer.create_stream()
            stream.accept_waveform(16000, normalize_gain(samples))
            self._recognizer.decode_stream(stream)
            text = stream.result.text.strip()
            seconds = time.perf_counter() - started
            return AsrResult(text=text, seconds=seconds, audio_seconds=len(samples) / 16000)


    class FinalASR:
        """保留原统一入口，内部固定使用 Parakeet，旧配置不会再切换模型。"""

        def __init__(self, engine: str = "parakeet", num_threads: int = 6, cloud=None):  # noqa: ARG002
            self.engine = "parakeet"
            self.num_threads = num_threads
            self._impl = None
            self._lock = threading.RLock()

        def load(self) -> None:
            with self._lock:
                if self._impl is None:
                    impl = _Parakeet(self.num_threads)
                    impl.load()
                    self._impl = impl

        def transcribe(self, samples: np.ndarray, context: str = "") -> AsrResult:  # noqa: ARG002
            with self._lock:
                self.load()
                return self._impl.transcribe(samples)

        @staticmethod
        def available(engine: str = "parakeet") -> bool:
            return engine == "parakeet" and all(
                (MODEL_DIR / filename).is_file()
                for filename in ("model.int8.onnx", "tokens.txt")
            )


    def decode_wav(path: str | Path) -> np.ndarray:
        """读取 16-bit PCM WAV，转换为 16kHz 单声道 float32。"""
        with wave.open(str(path), "rb") as handle:
            rate = handle.getframerate()
            frames = handle.getnframes()
            channels = handle.getnchannels()
            width = handle.getsampwidth()
            raw = handle.readframes(frames)
        if width != 2:
            raise ValueError("仅支持 16bit PCM wav")
        data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
        if channels > 1:
            data = data.reshape(-1, channels).mean(axis=1)
        if rate != 16000:
            import soxr

            data = soxr.resample(data, rate, 16000)
        return data.astype(np.float32)
# END MODULE: jpsub.core.asr

# ======================================================================
# BEGIN MODULE: jpsub.core.audio  (jpsub/core/audio.py)
# ======================================================================
if False:  # 可阅读的源码区块（独立模块由上方加载器执行）
    # -*- coding: utf-8 -*-
    """音频采集：系统声音（WASAPI loopback）/ 麦克风，统一输出 16kHz 单声道。"""
    # __FUTURE_IMPORT__ from __future__ import annotations

    import threading
    from typing import Callable, List

    import numpy as np

    import soundcard as sc
    import soxr

    TARGET_RATE = 16000


    def list_devices() -> dict[str, List[str]]:
        """列出可用的系统声音（loopback）与麦克风设备名。"""
        loopback, mic = [], []
        try:
            for m in sc.all_microphones(include_loopback=True):
                if getattr(m, "isloopback", False):
                    loopback.append(m.name)
                else:
                    mic.append(m.name)
        except Exception:  # noqa: BLE001
            pass
        return {"loopback": loopback, "mic": mic}


    def _pick_device(source: str, name: str):
        """根据来源与设备名找到 soundcard 设备对象。"""
        devices = [d for d in sc.all_microphones(include_loopback=True)
                   if bool(d.isloopback) == (source == "loopback")]
        if name:
            for device in devices:
                if name in (device.name, device.id):
                    return device
            # Explicit selection is not auto mode: never capture another source silently.
            raise RuntimeError(f"指定的音频设备不可用：{name}，请重新选择或改为自动")
        if source == "loopback":
            spk = sc.default_speaker()
            if spk is None:
                raise RuntimeError("没有可用的默认扬声器，请连接耳机或启用输出设备")
            for device in devices:
                if device.id == spk.id or device.name == spk.name:
                    return device
            raise RuntimeError("默认输出设备不支持系统声音采集")
        return sc.default_microphone()


    class AudioCapture(threading.Thread):
        """后台采集线程：按块读取音频，重采样为 16k 单声道后回调。"""

        def __init__(
            self,
            source: str,
            device_name: str,
            on_chunk: Callable[[np.ndarray, float], None],
            on_error: Callable[[str], None],
            block_ms: int = 80,
            on_status: Callable[[str], None] | None = None,
        ):
            super().__init__(daemon=True, name="AudioCapture")
            self.source = source
            self.device_name = device_name
            self.on_chunk = on_chunk
            self.on_error = on_error
            self.block_ms = block_ms
            self._stop_event = threading.Event()
            self.on_status = on_status or (lambda text: None)
            self.sample_rate = 48000

        def stop(self) -> None:
            self._stop_event.set()

        # ------------------------------------------------------------------
        def run(self) -> None:  # noqa: C901
            try:
                device = _pick_device(self.source, self.device_name)
                if device is None:
                    raise RuntimeError("没有可用的麦克风")
                self.on_status(f"正在采集：{device.name}")
            except Exception as e:  # noqa: BLE001
                self.on_error(f"找不到音频设备：{e}")
                return

            # 探测设备原生采样率（loopback 一般 48000 或 44100）
            native = 48000
            try:
                native = int(round(device.samplerate)) if getattr(device, "samplerate", None) else 48000
            except Exception:  # noqa: BLE001
                native = 48000
            if native not in (44100, 48000, 16000, 22050, 32000, 88200, 96000, 11025, 8000):
                native = 48000
            self.sample_rate = native

            block = max(160, int(native * self.block_ms / 1000))
            resampler = (soxr.ResampleStream(native, TARGET_RATE, 1, dtype="float32", quality="HQ")
                         if native != TARGET_RATE else None)
            silent_samples = 0
            silence_warned = False

            try:
                # WASAPI 的强制单声道录音可能产生异常数据。保留原始声道，再在软件里混音。
                recorder = device.recorder(samplerate=native, channels=None, blocksize=block)
                with recorder as rec:
                    while not self._stop_event.is_set():
                        data = rec.record(numframes=block)
                        if self._stop_event.is_set():
                            break
                        if data is None or len(data) == 0:
                            continue
                        data = np.asarray(data, dtype=np.float32)
                        mono = data.mean(axis=1) if data.ndim == 2 else data.reshape(-1)
                        mono = np.nan_to_num(mono)
                        if resampler is not None:
                            mono = resampler.resample_chunk(mono)
                        if mono.size == 0:
                            continue
                        rms = float(np.sqrt(np.mean(mono**2) + 1e-12))
                        silent_samples = silent_samples + mono.size if rms < 1e-5 else 0
                        if silent_samples > TARGET_RATE * 8 and not silence_warned:
                            silence_warned = True
                            self.on_status("没有采集到声音：请确认视频正在播放，并选择视频实际使用的输出设备")
                        elif rms >= 1e-5 and silence_warned:
                            silence_warned = False
                            self.on_status(f"正在采集：{device.name}")
                        self.on_chunk(mono, rms)
            except Exception as e:  # noqa: BLE001
                if not self._stop_event.is_set():
                    self.on_error(f"音频采集出错：{e}")


    def normalize_gain(samples: np.ndarray, target_peak: float = 0.85, max_gain: float = 6.0) -> np.ndarray:
        """轻度自动增益，让小声的直播也能被稳定识别。"""
        if samples.size == 0:
            return samples
        peak = float(np.max(np.abs(samples)))
        if peak < 1e-4:
            return samples
        gain = min(max_gain, target_peak / peak)
        if gain <= 1.02:
            return samples
        return np.clip(samples * gain, -1.0, 1.0).astype(np.float32)
# END MODULE: jpsub.core.audio

# ======================================================================
# BEGIN MODULE: jpsub.core.config  (jpsub/core/config.py)
# ======================================================================
if False:  # 可阅读的源码区块（独立模块由上方加载器执行）
    # -*- coding: utf-8 -*-
    """配置管理：默认值、JSON 持久化、翻译/识别服务预设。"""
    # __FUTURE_IMPORT__ from __future__ import annotations

    import copy
    import json
    import os
    import tempfile
    import threading
    import time
    from contextlib import contextmanager
    from pathlib import Path
    from typing import Any

    from ..paths import CONFIG_PATH

    # ---------------------------------------------------------------- 服务预设
    # only: llama.cpp / Microsoft Free / Google Free
    TRANSLATE_PRESETS: dict[str, dict] = {
        "llamacpp": dict(label="本地 · 混元 Hy-MT2 7B（离线）", kind="llamacpp", base_url="", model="",
                         key_hint="固定 Hy-MT2 7B；可选 CPU、Vulkan、CUDA 推理引擎。"),
        "ms-free": dict(label="免费 · 微软翻译（免密钥）", kind="msfree", base_url="", model="",
                        key_hint="非官方免密钥接口，服务状态可能变化。", unofficial=True),
        "google-free": dict(label="免费 · 谷歌翻译（免密钥）", kind="googlefree", base_url="", model="",
                            key_hint="非官方免密钥接口，须能访问谷歌。", unofficial=True),
    }

    # 日语识别只保留一个经过取舍的本地模型，避免用户在相似选项中反复试错。
    FINAL_ENGINES: dict[str, dict] = {
        "parakeet": dict(label="日语高速识别（Parakeet 0.6B）",
                         path="parakeet-ja-0.6b-int8", kind="sherpa", download="parakeet-ja"),
    }


    def _defaults() -> dict:
        return {
            "version": 1,
            "model_setup_version": 4,
            "audio": {"source": "loopback", "device": "", "block_ms": 80},
            "vad": {"threshold": 0.4, "min_silence_ms": 350, "min_speech_ms": 200, "max_segment_s": 10},
            "asr": {
                "partial": True,
                "draft_mode": "rolling",     # rolling=滚动识别 / off=关闭实时草稿
                "draft_interval_ms": 500,
                "draft_threads": 4,
                "final_engine": "parakeet",
                "final_threads": 6,
                "max_segment_s": 10,
                "context_prompt": False,
            },
            "translate": {
                "enabled": True,
                "provider": "llamacpp",
                "auto_fallback": False,
                "live_provider": "same",
                "live": True,
                "live_min_interval_ms": 450,
                "live_min_new_chars": 2,
                "context_lines": 3,
                # 最终译文流式更新间隔，旧版本硬编码 40ms；用户未调节时保持原行为。
                "final_stream_interval_ms": 40,
                "glossary": [],
                "services": {"llamacpp": {"model": "models/llm/Hy-MT2-7B-Q4_K_M.gguf", "variant": "auto"}},
            },
            "ui": {
                "theme": "dark",
                "accent": "#ff86b3",
                "bg": "auto",
                "bg_blur": 16,
                "bg_dim": 45,
                "bg_opacity": 100,
                "font": "Microsoft YaHei UI",
                "jp_size": 13,
                "zh_size": 19,
                "max_lines": 8,  # legacy setting, no longer controls memory retention
                "history_limit": 3,  # 只在内存保留最近 3 条完整字幕及其译文
                "display": "both",  # both / zh / jp
                "show_jp_in_history": True,
                "window": {"w": 1220, "h": 720, "x": None, "y": None, "on_top": False},
            },
            "overlay": {
                "enabled": False, "lines": 2, "zh_size": 24, "jp_size": 15,
                "font_name": "Microsoft YaHei", "current_bold": True,
                "current_color": "#ffffff", "translation_color": "#d0d0d0",
                "previous_color": "#9a9a9a", "background_color": "#000000",
                "opacity": 85, "text_shadow": True, "show_jp": True,
                "click_through": False, "locked": False,
                "x": None, "y": None, "w": 940, "h": 150,
            },
        }


    def _deep_merge(base: dict, override: dict) -> dict:
        out = copy.deepcopy(base)
        for k, v in (override or {}).items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = _deep_merge(out[k], v)
            else:
                out[k] = copy.deepcopy(v)
        return out


    @contextmanager
    def _config_save_lock(path: Path):
        """跨进程写锁：两个窗口写同一 config 时避免互相覆盖。"""
        lock_path = path.with_name(path.name + ".lock")
        with lock_path.open("a+b") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(bytes([0]))
                handle.flush()
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


    def _read_json_retry(path: Path) -> Any:
        """On Windows, retry transient sharing failures without masking bad JSON."""
        deadline = time.monotonic() + 0.75
        while True:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except PermissionError:
                if os.name != "nt" or time.monotonic() >= deadline:
                    raise
                time.sleep(0.01)


    class Config:
        """线程安全的配置对象（dict 风格访问）。"""

        def __init__(self, path: Path = CONFIG_PATH):
            self.path = Path(path)
            self._lock = threading.RLock()
            self._pending: dict[str, Any] = {}
            self.load_error = ""           # Corrupted files remain untouched, with visible diagnostics.
            self.data = _defaults()
            self.load()

        # ------------------------------------------------------------------
        def load(self) -> None:
            self.load_error = ""
            if self.path.exists():
                try:
                    # Readers and writers use the same lock, so a second app
                    # cannot observe the save transaction half-complete.
                    with _config_save_lock(self.path):
                        user = _read_json_retry(self.path)
                    if not isinstance(user, dict):
                        raise ValueError("配置文件根节点必须为 JSON 对象")
                    if int(user.get('model_setup_version', 0)) < 3:
                        # 旧版本的高门限和备用识别设置会让轻声、短句无法进入识别。
                        user.setdefault('vad', {}).update(threshold=0.4, min_silence_ms=500, max_segment_s=18)
                        asr = user.setdefault('asr', {})
                        asr.update(final_engine='parakeet', max_segment_s=18, context_prompt=False)
                        for name in ('cloud', 'streaming', 'stream_model'):
                            asr.pop(name, None)
                        translation = user.setdefault('translate', {})
                        translation['live_provider'] = 'same'
                        local = translation.setdefault('services', {}).setdefault('llamacpp', {})
                        if not local.get('model') or 'translategemma' in str(local['model']).lower():
                            local['model'] = 'models/llm/Hy-MT2-1.8B-Q4_K_M.gguf'
                        user['model_setup_version'] = 3
                    if int(user.get('model_setup_version', 0)) < 4:
                        user.setdefault('asr', {}).update(final_engine='parakeet', draft_interval_ms=500, max_segment_s=10)
                        user.setdefault('vad', {}).update(min_silence_ms=350, max_segment_s=10)
                        user.setdefault('translate', {}).update(live_provider='same', live_min_interval_ms=450, live_min_new_chars=2)
                        local = user.setdefault('translate', {}).setdefault('services', {}).setdefault('llamacpp', {})
                        if not local.get('model') or 'hy-mt2-1.8b' in str(local['model']).lower():
                            local['model'] = 'models/llm/Hy-MT2-7B-Q4_K_M.gguf'
                        user['model_setup_version'] = 4
                    # 兼容旧配置：过时服务不再被激活，保留旧 API 设置供手动备份。
                    translation = user.setdefault('translate', {})
                    if translation.get('provider') not in TRANSLATE_PRESETS:
                        translation['provider'] = 'llamacpp'
                    if translation.get('live_provider') not in ('auto', 'same'):
                        translation['live_provider'] = 'same'
                    local = translation.setdefault('services', {}).setdefault('llamacpp', {})
                    local['model'] = _defaults()['translate']['services']['llamacpp']['model']
                    with self._lock:
                        self.data = _deep_merge(_defaults(), user)
                        self._pending.clear()
                except Exception as exc:  # noqa: BLE001 Never overwrite an unreadable original.
                    self.load_error = f"配置文件无法读取（原文件已保留）：{exc}"

        @staticmethod
        def _validate_set(path: str, value: Any) -> None:
            if path == "translate.provider" and value not in TRANSLATE_PRESETS:
                raise ValueError(f"不支持的翻译服务：{value}")
            if path == "translate.live_provider" and value not in ("auto", "same"):
                raise ValueError(f"不支持的草稿翻译服务：{value}")

        def save(self) -> None:
            """仅提交本实例改动的键，避免旧界面覆盖新 VAD/翻译参数。"""
            with self._lock:
                if not self._pending and self.path.is_file():
                    return  # 旧窗口中无变化的保存操作不应覆盖另一窗口写入的设置。
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with _config_save_lock(self.path):
                    if self.path.is_file():
                        try:
                            current = _read_json_retry(self.path)
                            if not isinstance(current, dict):
                                raise ValueError("配置文件内容不是 JSON 对象")
                        except (ValueError, UnicodeError) as exc:
                            self.load_error = f"配置文件损坏，原文件已保留，拒绝覆盖：{exc}"
                            raise RuntimeError(self.load_error) from exc
                        merged = _deep_merge(_defaults(), current)
                    else:
                        merged = _deep_merge(_defaults(), self.data)
                    for path, value in self._pending.items():
                        node = merged
                        keys = path.split(".")
                        for key in keys[:-1]:
                            node = node.setdefault(key, {})
                        node[keys[-1]] = copy.deepcopy(value)
                    fd, name = tempfile.mkstemp(dir=self.path.parent, prefix=".config-", suffix=".tmp")
                    temp = Path(name)
                    try:
                        with os.fdopen(fd, "w", encoding="utf-8", newline=None) as stream:
                            json.dump(merged, stream, indent=2, ensure_ascii=False)
                            stream.write(chr(10))
                            stream.flush()
                            os.fsync(stream.fileno())
                        # On Windows an unsynchronized reader may briefly hold
                        # the destination open without FILE_SHARE_DELETE. Keep
                        # the cross-process writer lock while retrying; never
                        # delete the original or publish a partial JSON file.
                        deadline = time.monotonic() + 0.75
                        while True:
                            try:
                                os.replace(temp, self.path)
                                break
                            except PermissionError:
                                if os.name != "nt" or time.monotonic() >= deadline:
                                    raise
                                time.sleep(0.01)
                    finally:
                        temp.unlink(missing_ok=True)
                    self.data = merged
                    self.load_error = ""
                    self._pending.clear()

        # ------------------------------------------------------------------
        def get(self, path: str, default: Any = None) -> Any:
            with self._lock:
                node: Any = self.data
                for part in path.split("."):
                    if isinstance(node, dict) and part in node:
                        node = node[part]
                    else:
                        return default
                return node

        def set(self, path: str, value: Any, save: bool = True) -> None:
            self._validate_set(path, value)
            with self._lock:
                node = self.data
                parts = path.split(".")
                for part in parts[:-1]:
                    node = node.setdefault(part, {})
                node[parts[-1]] = copy.deepcopy(value)
                self._pending[path] = copy.deepcopy(value)
                if save:
                    self.save()

        def update_many(self, mapping: dict[str, Any], save: bool = True) -> None:
            # 全部校验成功后才开始更新，避免在不合法服务等错误中途留下半份新设置。
            for key, value in mapping.items():
                self._validate_set(key, value)
            with self._lock:
                for key, value in mapping.items():
                    self.set(key, value, save=False)
                if save:
                    self.save()

        # ------------------------------------------------------------------
        def service(self, provider: str) -> dict:
            """返回某个翻译服务的有效配置（预设 + 用户覆盖）。"""
            if provider not in TRANSLATE_PRESETS:
                raise ValueError(f"不支持的翻译服务：{provider}")
            preset = TRANSLATE_PRESETS[provider]
            user = self.get(f"translate.services.{provider}", {}) or {}
            merged = {
                "provider": provider,
                "kind": preset["kind"],
                "label": preset["label"],
                "base_url": user.get("base_url") or preset.get("base_url", ""),
                "model": (_defaults()["translate"]["services"]["llamacpp"]["model"]
                          if provider == "llamacpp" else user.get("model") or preset.get("model", "")),
                "api_key": user.get("api_key", ""),
            }
            return merged

        def set_service(self, provider: str, **fields: Any) -> None:
            if provider not in TRANSLATE_PRESETS:
                raise ValueError(f"不支持的翻译服务：{provider}")
            if provider == "llamacpp" and "model" in fields:
                fields["model"] = _defaults()["translate"]["services"]["llamacpp"]["model"]
            # Commit only the changed leaves in one locked save transaction.
            # A stale service snapshot must never overwrite other processes' fields.
            # Concurrent writes to the same leaf resolve by commit/lock order:
            # the later successful locked commit wins for that leaf alone.
            if fields:
                self.update_many(
                    {f"translate.services.{provider}.{key}": value
                     for key, value in fields.items()}
                )
# END MODULE: jpsub.core.config

# ======================================================================
# BEGIN MODULE: jpsub.core.http_util  (jpsub/core/http_util.py)
# ======================================================================
if False:  # 可阅读的源码区块（独立模块由上方加载器执行）
    # -*- coding: utf-8 -*-
    """HTTP 客户端工具：本地地址自动绕过系统代理（避免 Clash 等代理拦截 127.0.0.1）。"""
    # __FUTURE_IMPORT__ from __future__ import annotations

    from urllib.parse import urlsplit

    import httpx

    _LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}
    _UNSET = object()
    _SYS_PROXY: object = _UNSET


    def system_proxy() -> str | None:
        """读 Windows 的「系统代理」（Clash / v2ray 之类），没有就返回 None。

        有些机器上局域网直连 GitHub 很慢、开代理反而快很多，所以下载引擎时优先用它。
        """
        global _SYS_PROXY
        if _SYS_PROXY is _UNSET:
            value: str | None = None
            try:
                import winreg

                key_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as k:
                    enable, _ = winreg.QueryValueEx(k, "ProxyEnable")
                    if enable:
                        server, _ = winreg.QueryValueEx(k, "ProxyServer")
                        server = str(server or "").strip()
                        if "=" in server:      # 形如 http=127.0.0.1:7897;https=127.0.0.1:7897
                            parts = dict(p.split("=", 1) for p in server.split(";") if "=" in p)
                            server = (parts.get("https") or parts.get("http") or "").strip()
                        if server and not server.startswith("http"):
                            server = "http://" + server
                        value = server or None
            except Exception:  # noqa: BLE001
                value = None
            if not value:
                value = _env_proxy() or _probe_local_proxy()
            _SYS_PROXY = value
        return _SYS_PROXY if isinstance(_SYS_PROXY, str) else None


    def _env_proxy() -> str | None:
        import os

        for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY"):
            v = str(os.environ.get(name) or "").strip()
            if v:
                return v if v.startswith("http") else "http://" + v
        return None


    def _probe_local_proxy() -> str | None:
        """很多代理软件（Clash / v2rayN 等）只在本地监听端口、不写系统代理，按常见端口试一下。"""
        import socket

        for port in (7897, 7890, 7891, 10809, 10808, 1080, 2080):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.15):
                    return f"http://127.0.0.1:{port}"
            except Exception:  # noqa: BLE001
                continue
        return None


    def is_local_url(url: str) -> bool:
        try:
            host = (urlsplit(url).hostname or "").lower()
        except Exception:  # noqa: BLE001
            return False
        return host in _LOCAL_HOSTS or host.startswith("127.")


    def make_client(url: str = "", timeout=30.0, **kwargs) -> httpx.Client:
        """创建 httpx 客户端；本地地址不使用环境代理，远程地址照常使用。"""
        kwargs.setdefault("follow_redirects", True)
        return httpx.Client(timeout=timeout, trust_env=not is_local_url(url), **kwargs)
# END MODULE: jpsub.core.http_util

# ======================================================================
# BEGIN MODULE: jpsub.core.llama_engine  (jpsub/core/llama_engine.py)
# ======================================================================
if False:  # 可阅读的源码区块（独立模块由上方加载器执行）
    # -*- coding: utf-8 -*-
    """内置本地大模型引擎（llama.cpp / llama-server）：下载、启动、停止、健康检查。

    不需要用户安装 Ollama；引擎随软件分发（约 47MB），模型使用 GGUF 文件。
    """
    # __FUTURE_IMPORT__ from __future__ import annotations

    import atexit
    import ctypes
    import os
    import socket
    import subprocess
    import threading
    import time
    import zipfile
    from pathlib import Path
    from typing import Callable, Optional

    import httpx

    try:                     # psutil 在 requirements.txt 里；万一环境装漏了也不该连引擎都用不了
        import psutil
    except Exception:  # noqa: BLE001
        psutil = None  # type: ignore[assignment]

    ROOT = Path(__file__).resolve().parents[2]
    ENGINE_DIR = ROOT / "engine"
    from ..paths import MODELS
    MODELS_LLM = MODELS / "llm"

    ENGINE_TAG = "b11541"
    _ASSET = "llama-{tag}-bin-win-{variant}-x64.zip"
    _RELEASE = "https://github.com/ggml-org/llama.cpp/releases/download/{tag}/{asset}"
    _MIRROR = "https://ghproxy.net/" + _RELEASE  # 国内加速镜像（GitHub 直连不通时自动切换）

    # cpu / vulkan / cuda；cuda 需要额外下载 CUDA 运行库（cudart），两个包都解压到同一目录
    VARIANTS = ("cpu", "vulkan", "cuda")
    ASSETS: dict[str, list[str]] = {
        "cpu": ["llama-{tag}-bin-win-cpu-x64.zip"],
        "vulkan": ["llama-{tag}-bin-win-vulkan-x64.zip"],
        "cuda": ["llama-{tag}-bin-win-cuda-12.4-x64.zip",
                 "cudart-llama-bin-win-cuda-12.4-x64.zip"],
    }
    GPU_VARIANTS = ("vulkan", "cuda")     # 这些变体要用显卡
    ProgressCb = Optional[Callable[[str, int, int], None]]

    MODEL_MIRRORS = ("https://hf-mirror.com", "https://huggingface.co")
    RECOMMENDED_MODELS = [
        dict(
            name="Hy-MT2-7B-Q4_K_M.gguf",
            repo="tencent/Hy-MT2-7B-GGUF",
            desc="混元 Hy-MT2 7B（自然口语 · 推荐）",
            size_gb=4.62,
            sha256="9f96256500f3fc1ab4d64336b58f52a949a95ad7516b0c229476eef782f9f77b",
        ),
    ]


    def download_model(item: dict, on_progress: ProgressCb = None) -> Path:
        """下载推荐 GGUF 模型（hf-mirror 国内镜像优先，支持断点续传）。"""
        filename = str(item.get("name") or "")
        repo = str(item.get("repo") or "")
        if not filename or not repo:
            raise RuntimeError("模型配置不完整")
        MODELS_LLM.mkdir(parents=True, exist_ok=True)
        dest = MODELS_LLM / filename
        if valid_model(dest):
            return dest
        part = MODELS_LLM / (filename + ".part")
        timeout = httpx.Timeout(connect=20.0, read=45.0, write=20.0, pool=20.0)
        last_err: Exception | None = None
        for base in MODEL_MIRRORS:
            url = f"{base}/{repo}/resolve/main/{filename}"
            for _attempt in range(4):
                try:
                    already = part.stat().st_size if part.exists() else 0
                    headers = {"Range": f"bytes={already}-"} if already else {}
                    with httpx.stream("GET", url, headers=headers, timeout=timeout,
                                      follow_redirects=True) as r:
                        if r.status_code == 416 and already:
                            part.unlink(missing_ok=True)
                            continue
                        if already and r.status_code == 200:
                            already = 0
                        if r.status_code not in (200, 206):
                            r.raise_for_status()
                        remaining = int(r.headers.get("content-length") or 0)
                        total = (already + remaining) if r.status_code == 206 else remaining
                        done = already
                        mode = "ab" if r.status_code == 206 else "wb"
                        with open(part, mode) as f:
                            for chunk in r.iter_bytes(1 << 16):
                                f.write(chunk)
                                done += len(chunk)
                                if on_progress and (done % (1 << 20) < (1 << 16)):
                                    on_progress(f"正在下载模型（{filename}）…", done, total)
                    size = part.stat().st_size if part.exists() else 0
                    if total and size < total:
                        if on_progress:
                            on_progress("连接中断，正在断点续传…", size, total)
                        time.sleep(1.0)
                        continue
                    if not valid_model(part):
                        raise RuntimeError('下载的文件不是完整 GGUF 模型，请重试')
                    if item.get('sha256'):
                        import hashlib
                        with part.open('rb') as handle:
                            digest = hashlib.file_digest(handle, 'sha256').hexdigest()
                        if digest != item['sha256']:
                            part.unlink(missing_ok=True)
                            raise RuntimeError('模型校验失败，正在重新下载')
                    part.replace(dest)
                    return dest
                except Exception as e:  # noqa: BLE001
                    last_err = e
                    time.sleep(1.5)
                    continue
        raise RuntimeError(f"模型下载失败：{last_err}")


    def engine_dir(variant: str) -> Path:
        return ENGINE_DIR / variant


    def server_exe(variant: str) -> Path:
        return engine_dir(variant) / "llama-server.exe"


    def installed(variant: str) -> bool:
        directory = engine_dir(variant)
        required = ['llama-server.exe', 'llama-server-impl.dll', 'llama.dll', 'ggml.dll', 'ggml-base.dll']
        if variant == 'vulkan':
            required.append('ggml-vulkan.dll')
        elif variant == 'cuda':
            required += ['ggml-cuda.dll', 'cudart64_12.dll', 'cublas64_12.dll', 'cublasLt64_12.dll']
        return all((directory / name).is_file() for name in required) and bool(list(directory.glob('ggml-cpu*.dll')))


    def installed_variants() -> list[str]:
        return [v for v in VARIANTS if installed(v)]


    _nvidia_cache: bool | None = None


    def preferred_variant(cfg, fallback: str = "cpu") -> str:
        """当前该用哪个引擎：先看设置里选的，没装就在已装的里挑（CUDA > Vulkan > CPU）。"""
        want = str(cfg.get("translate.services.llamacpp.variant", "") or "")
        if want and installed(want):
            return want
        for v in (("cuda", "vulkan", "cpu") if nvidia_available() else ("vulkan", "cpu")):
            if installed(v):
                return v
        return want or fallback


    def nvidia_available() -> bool:
        """粗略判断这台机器有没有 NVIDIA 显卡（用来决定要不要显示 CUDA 引擎）。"""
        global _nvidia_cache
        if _nvidia_cache is None:
            import shutil

            ok = bool(shutil.which("nvidia-smi"))
            if not ok:
                sys32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
                ok = any((sys32 / n).exists() for n in ("nvcuda.dll", "nvml.dll"))
            _nvidia_cache = ok
        return _nvidia_cache


    # SHA-256 digests from official ggml-org/llama.cpp release b11541, pinned
    # here rather than downloaded from whichever mirror serves the archive.
    _TRUSTED_ENGINE_ZIP_SHA256 = {
        "llama-b11541-bin-win-cpu-x64.zip": "cdc0535d11038bb337dfba3c15682050eaa9c07aedd0f915b4c09e8a8e8c0a5c",
        "llama-b11541-bin-win-vulkan-x64.zip": "37bba511d120222f13c3d520dd875f739a530cc124e78f7cbce0026de0173d8a",
        "llama-b11541-bin-win-cuda-12.4-x64.zip": "c5ccdd22e6b11c013efd6a931f93c3707e6fa5ab2f90df5c7d1838785540ece3",
        "cudart-llama-bin-win-cuda-12.4-x64.zip": "8c79a9b226de4b3cacfd1f83d24f962d0773be79f1e7b75c6af4ded7e32ae1d6",
    }
    _MAX_ENGINE_ZIP_BYTES = 900 * 1024 * 1024
    _MAX_ENGINE_UNPACKED_BYTES = 3 * 1024 * 1024 * 1024
    _MAX_ENGINE_ZIP_FILES = 1500


    def _verified_engine_archive(zip_path: Path, target: Path, remaining_budget: int) -> int:
        """Reject untrusted ZIP members before extracting anything to a staging dir."""
        import stat

        extracted_bytes = 0
        with zipfile.ZipFile(zip_path) as z:
            items = z.infolist()
            if len(items) > _MAX_ENGINE_ZIP_FILES:
                raise RuntimeError("引擎压缩包文件数量异常")
            for item in items:
                member = item.filename.replace(chr(92), "/")
                if not member or member.startswith("/") or ":" in member or chr(0) in member:
                    raise RuntimeError("引擎压缩包包含非法路径")
                parts = member.rstrip("/").split("/")
                if any(p in ("", ".", "..") for p in parts) or len(parts) > 8:
                    raise RuntimeError("引擎压缩包包含不安全的嵌套路径")
                mode = (item.external_attr >> 16) & 0o170000
                if mode == stat.S_IFLNK:
                    raise RuntimeError("引擎压缩包包含符号链接")
                if item.file_size > remaining_budget - extracted_bytes:
                    raise RuntimeError("引擎解压后的体积超过安全限制")
                extracted_bytes += item.file_size
            # ZIP entry list and limits have been validated; source SHA was
            # checked before calling this function.
            z.extractall(target)
        return extracted_bytes


    def download_engine(variant: str, on_progress: ProgressCb = None) -> Path:
        """Install an official, hash-verified llama.cpp engine via rollback-safe staging."""
        import hashlib
        import shutil
        import tempfile

        if variant not in VARIANTS:
            raise RuntimeError(f"未知引擎版本：{variant}")
        ENGINE_DIR.mkdir(parents=True, exist_ok=True)
        dest = engine_dir(variant)
        from .http_util import system_proxy

        with tempfile.TemporaryDirectory(prefix=".verified-engine-", dir=ENGINE_DIR) as work:
            workdir = Path(work)
            staging = workdir / "payload"
            staging.mkdir()
            budget = _MAX_ENGINE_UNPACKED_BYTES
            for pattern in ASSETS[variant]:
                asset = pattern.format(tag=ENGINE_TAG)
                expected_sha = _TRUSTED_ENGINE_ZIP_SHA256.get(asset)
                if expected_sha is None:
                    raise RuntimeError(f"当前引擎版本没有可信校验值：{asset}；拒绝安装")
                direct = _RELEASE.format(tag=ENGINE_TAG, asset=asset)
                mirror = _MIRROR.format(tag=ENGINE_TAG, asset=asset)
                proxy = system_proxy()
                attempts = ([(direct, proxy)] if proxy else []) + [(direct, None), (mirror, None)]
                zip_path = workdir / asset
                last_error = None
                for url, using_proxy in attempts:
                    try:
                        if on_progress:
                            on_progress(f"正在校验下载：{variant} / {asset}", 0, 0)
                        digest = hashlib.sha256()
                        received = 0
                        limits = httpx.Timeout(connect=20.0, read=60.0, write=20.0, pool=20.0)
                        with httpx.stream("GET", url, follow_redirects=True, timeout=limits,
                                          proxy=using_proxy) as response:
                            response.raise_for_status()
                            declared = int(response.headers.get("content-length") or 0)
                            if declared > _MAX_ENGINE_ZIP_BYTES:
                                raise RuntimeError("引擎下载文件过大")
                            with zip_path.open("wb") as output:
                                for piece in response.iter_bytes(1 << 16):
                                    received += len(piece)
                                    if received > _MAX_ENGINE_ZIP_BYTES:
                                        raise RuntimeError("引擎下载体积超过限制")
                                    digest.update(piece)
                                    output.write(piece)
                                    if on_progress and (received % (1 << 20) < len(piece)):
                                        on_progress("正在下载并验证完整性…", received, declared)
                        if digest.hexdigest() != expected_sha:
                            raise RuntimeError("引擎 SHA-256 校验失败，下载文件已拒绝安装")
                        break
                    except Exception as exc:  # noqa: BLE001
                        last_error = exc
                        zip_path.unlink(missing_ok=True)
                else:
                    raise RuntimeError(f"引擎下载或校验失败（{asset}）：{last_error}")
                if on_progress:
                    on_progress(f"校验成功，正在安全解压 {asset}…", 1, 1)
                budget -= _verified_engine_archive(zip_path, staging, budget)
                zip_path.unlink(missing_ok=True)

            _flatten_dir(staging)
            if not (staging / "llama-server.exe").is_file():
                raise RuntimeError("已验证引擎缺少 llama-server.exe；原有引擎未被修改")
            # Replace entire engine variant only after ALL downloads verify.
            # Roll back the previous directory on failure (e.g. DLL in use).
            previous = workdir / "previous"
            had_previous = dest.exists()
            if had_previous:
                dest.replace(previous)
            try:
                staging.replace(dest)
            except BaseException:
                if had_previous and previous.exists() and not dest.exists():
                    previous.replace(dest)
                raise
            if on_progress:
                on_progress("引擎已完成完整性验证并安装", 1, 1)
        return dest


    def _flatten_dir(dest: Path) -> None:
        """有些包解压后带一层子目录，把里面的文件提到引擎根目录（dll 必须和 exe 同级）。"""
        for sub in [d for d in dest.iterdir() if d.is_dir()]:
            for f in list(sub.iterdir()):
                if f.is_file() and not (dest / f.name).exists():
                    f.replace(dest / f.name)


    # ---------------------------------------------------------------- 模型管理
    def list_gguf(folder: Path | None = None) -> list[Path]:
        d = folder or MODELS_LLM
        if not d.exists():
            return []
        return sorted((p for p in d.glob("*.gguf") if valid_model(p)), key=lambda p: p.stat().st_size)


    def valid_model(path: Path) -> bool:
        try:
            if path.stat().st_size < 1024 * 1024:
                return False
            with path.open('rb') as f:
                return f.read(4) == b'GGUF'
        except OSError:
            return False


    def resolve_model(preferred: str = "") -> Path | None:
        """仅加载随附的混元 Hy-MT2 7B；忽略旧版自定义模型路径。"""
        model = MODELS_LLM / RECOMMENDED_MODELS[0]["name"]
        return model if valid_model(model) else None


    # ---------------------------------------------------------------- 服务器
    def _free_port() -> int:
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        return port


    # ---------------------------------------------------------------- 随父进程退出
    _JOB_HANDLE: int | None = None
    _JOB_LOCK = threading.Lock()
    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
    _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9


    class _IoCounters(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


    class _BasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", ctypes.c_ulong),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", ctypes.c_ulong),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", ctypes.c_ulong),
            ("SchedulingClass", ctypes.c_ulong),
        ]


    class _ExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _BasicLimitInformation),
            ("IoInfo", _IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]


    def _keep_alive_job() -> int | None:
        """建一个「父进程一关就把子进程一起带走」的作业对象（Windows Job Object）。

        以前软件被强杀 / 崩溃时，llama-server 会留在后台：它占着 3~4GB 内存和显存，
        而新启动的引擎因为分不到显存直接加载失败（engine/server.log 里的
        OutOfDeviceMemory）。挂上这个作业对象后，父进程一消失子进程就会跟着退出。
        """
        global _JOB_HANDLE
        if os.name != "nt":
            return None
        with _JOB_LOCK:
            if _JOB_HANDLE is None:
                try:
                    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
                    k32.CreateJobObjectW.restype = ctypes.c_void_p
                    k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
                    handle = k32.CreateJobObjectW(None, None)
                    if not handle:
                        return None
                    info = _ExtendedLimitInformation()
                    info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                    if not k32.SetInformationJobObject(
                            ctypes.c_void_p(handle), _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                            ctypes.byref(info), ctypes.sizeof(info)):
                        return None
                    _JOB_HANDLE = int(handle)
                except Exception:  # noqa: BLE001
                    return None
            return _JOB_HANDLE


    def _join_job(pid: int) -> None:
        """把刚启动的引擎进程加进作业对象（失败也不影响正常使用）。"""
        handle = _keep_alive_job()
        if not handle:
            return
        try:
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.OpenProcess.restype = ctypes.c_void_p
            k32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
            PROCESS_SET_QUOTA, PROCESS_TERMINATE = 0x0100, 0x0001
            proc = k32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, False, int(pid))
            if not proc:
                return
            try:
                k32.AssignProcessToJobObject(ctypes.c_void_p(handle), ctypes.c_void_p(proc))
            finally:
                k32.CloseHandle(ctypes.c_void_p(proc))
        except Exception:  # noqa: BLE001
            pass


    def _has_running_yisheng_owner(proc) -> bool:
        """防止把另一份仍在运行的译声所启动的翻译引擎误判为残留。"""
        if psutil is None:
            return False
        try:
            parent = psutil.Process(proc.ppid())
            argv = [str(arg).lower().replace(chr(92), "/") for arg in parent.cmdline()]
            return any(arg.endswith("/yishengtranslator.pyw") for arg in argv) or (
                "jpsub.main" in argv and "python" in str(parent.name()).lower()
            )
        except psutil.NoSuchProcess:
            return False   # 真正的孤儿进程可以收回。
        except (psutil.AccessDenied, psutil.ZombieProcess, OSError):
            return True    # 无法确认属主时禁止误杀。


    def stale_servers(dry_run: bool = False) -> list[int]:
        """处理上次没退干净、还占着内存和显存的引擎进程，返回被结束的 PID。

        只认「本软件 engine 目录下」的 llama-server.exe，其它程序一概不碰。
        """
        if psutil is None:
            return []
        held = {srv._proc.pid for srv in list(_SERVERS.values()) if srv._proc is not None}
        me = os.getpid()
        try:
            root = str(ENGINE_DIR.resolve()).lower()
        except Exception:  # noqa: BLE001
            root = str(ENGINE_DIR).lower()
        found: list[int] = []
        for proc in psutil.process_iter(["pid", "name", "exe"]):
            try:
                pid = int(proc.info.get("pid") or 0)
                if pid in held or pid == me:
                    continue
                exe = str(proc.info.get("exe") or "")
                if not exe or os.path.basename(exe).lower() != "llama-server.exe":
                    continue
                if Path(exe).resolve().parent.parent != ENGINE_DIR.resolve():
                    continue
                if _has_running_yisheng_owner(proc):
                    continue
                found.append(pid)
                if dry_run:
                    continue
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except psutil.TimeoutExpired:
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess,
                    ValueError, OSError):
                continue
        return found


    def _diagnose_start_failure(err: Exception) -> str:
        """把引擎启动失败翻译成人话（日志里最常见的是显存不足）。"""
        tail = ""
        try:
            log = ENGINE_DIR / "server.log"
            if log.exists():
                tail = log.read_bytes()[-8192:].decode("utf-8", "ignore").lower()
        except Exception:  # noqa: BLE001
            tail = ""
        if "outofdevicememory" in tail or "failed to allocate" in tail:
            return ("显卡显存/内存不足，模型没能载入。可到「设置 → 翻译服务 → 用哪个引擎」"
                    "换成 CPU 引擎，或关掉占显存的其它程序后重试")
        if "failed to create context" in tail or "out of memory" in tail:
            return "模型载入时内存不够，没能建起上下文（可换小一点的模型或用 CPU 引擎）"
        return f"引擎启动失败：{err}"


    class LlamaServer:
        """管理一个 llama-server 进程。"""

        def __init__(self, model: Path, variant: str = "cpu", ctx: int = 2048, threads: int = 0, mmproj: Path | None = None):
            self.model = Path(model)
            self.variant = variant
            self.ctx = ctx
            self.mmproj = mmproj
            self.threads = threads or max(4, min(10, (os.cpu_count() or 8) // 2))
            self.port = _free_port()
            self._proc: subprocess.Popen | None = None

        @property
        def base_url(self) -> str:
            return f"http://127.0.0.1:{self.port}/v1"

        def start(self, on_status: Optional[Callable[[str], None]] = None, timeout: float = 240.0) -> None:
            exe = server_exe(self.variant)
            if not exe.exists():
                raise RuntimeError(f"引擎未下载（{self.variant}），请先在设置里点「下载引擎」")
            if not self.model.exists():
                raise RuntimeError(f"模型文件不存在：{self.model}")
            args = [
                str(exe), "-m", str(self.model), "-c", str(self.ctx), "-t", str(self.threads),
                "--host", "127.0.0.1", "--port", str(self.port),
                "-np", "1",
                "-b", "256", "-ub", "128", "--fit-target", "256",
                # This live translator handles many short, changing prompts.
                # The default 8192 MiB host prompt cache otherwise grows
                # across requests even while subtitle history stays bounded.
                # 0 disables host prompt caching; active KV context is still
                # bounded separately by -c and -np above.
                "--cache-ram", "0",
            ]
            if self.mmproj is not None:
                args += ["--mmproj", str(self.mmproj)]
            if self.variant in GPU_VARIANTS:
                args += ["-ngl", "auto"]
            ENGINE_DIR.mkdir(parents=True, exist_ok=True)
            log = open(ENGINE_DIR / "server.log", "ab")
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if on_status:
                on_status(f"正在启动本地引擎（{self.variant}），加载模型可能需要 5~30 秒…")
            try:
                self._proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
            finally:
                log.close()
            _join_job(self._proc.pid)
            t0 = time.time()
            while time.time() - t0 < timeout:
                if self._proc.poll() is not None:
                    raise RuntimeError("引擎进程已退出")
                if self.is_up():
                    return
                time.sleep(0.5)
            self.stop()
            raise RuntimeError("引擎启动超时（详情见 engine/server.log）")

        def is_up(self) -> bool:
            try:
                r = httpx.get(f"http://127.0.0.1:{self.port}/health", timeout=1.5, trust_env=False)
                return r.status_code == 200
            except Exception:  # noqa: BLE001
                return False

        def stop(self) -> None:
            proc = self._proc
            self._proc = None
            if proc is None:
                return
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=6)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception:  # noqa: BLE001
                pass


    _SERVERS: dict[str, LlamaServer] = {}
    _LOCK = threading.Lock()
    # 启动失败的记录：{model|variant: (失败时间, 说明)}。失败后一段时间内直接报错，
    # 不要每翻译一句就重新拉一个引擎进程（那正是会越跑越卡的元凶）。
    _FAILED: dict[str, tuple[float, str]] = {}
    _FAILED_COOLDOWN = 120.0


    def ensure_running(model: Path, variant: str = "cpu",
                       on_status: Optional[Callable[[str], None]] = None,
                       *, mmproj: Path | None = None, ctx: int = 2048) -> str:
        """确保引擎在运行并返回 OpenAI 兼容的 base_url（同一模型只启动一次）。"""
        key = f"{model.resolve()}|{variant}"
        hit = _FAILED.get(key)
        if hit is not None and time.time() - hit[0] < _FAILED_COOLDOWN:
            raise RuntimeError(hit[1])
        with _LOCK:
            srv = _SERVERS.get(key)
            if srv is not None and srv.is_up():
                return srv.base_url
            if srv is not None:
                srv.stop()
            # 先把上次没退干净的引擎收掉，否则显存/内存被老进程占着，新引擎会加载失败
            stale_servers()
            srv = LlamaServer(model, variant, ctx=ctx, mmproj=mmproj)
            try:
                srv.start(on_status=on_status, timeout=60.0 if variant in GPU_VARIANTS else 120.0)
            except Exception as e:  # noqa: BLE001
                srv.stop()
                msg = _diagnose_start_failure(e)
                _FAILED[key] = (time.time(), msg)
                raise RuntimeError(msg) from e
            _FAILED.pop(key, None)
            _SERVERS[key] = srv
            return srv.base_url


    def stop_translation(*, keep_variant: str | None = None) -> None:
        """清理不再使用的翻译引擎；可保留刚选中的变体。

        启动新变体与关闭旧变体使用相同的 _LOCK 串行化，以防新的 GPU 服务
        刚完成初始化就被上一轮设置变更误杀。直接调用无参数时保持原来清理全部的行为。
        """
        with _LOCK:
            for key, server in list(_SERVERS.items()):
                if server.mmproj is None and server.variant != keep_variant:
                    server.stop()
                    del _SERVERS[key]


    def stop_all() -> None:
        with _LOCK:
            for srv in list(_SERVERS.values()):
                try:
                    srv.stop()
                except Exception:  # noqa: BLE001
                    pass
            _SERVERS.clear()


    atexit.register(stop_all)
# END MODULE: jpsub.core.llama_engine

# ======================================================================
# BEGIN MODULE: jpsub.core.model_catalog  (jpsub/core/model_catalog.py)
# ======================================================================
if False:  # 可阅读的源码区块（独立模块由上方加载器执行）
    # -*- coding: utf-8 -*-
    """本地模型清单与下载（安装脚本 scripts/download_models.py 和设置面板共用一份）。

    默认走 hf-mirror.com 国内镜像；可用环境变量 HF_ENDPOINT 覆盖。
    """
    # __FUTURE_IMPORT__ from __future__ import annotations

    import os
    import time
    from pathlib import Path
    from typing import Callable, Optional

    ROOT = Path(__file__).resolve().parents[2]
    MODELS_DIR = ROOT / "models"

    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")

    ProgressCb = Optional[Callable[[str, int, int], None]]   # (文件名, 已下载, 总大小)

    # name -> 目标信息。desc 会显示在安装脚本和设置面板里。
    MODEL_TARGETS: dict[str, dict] = {
        "parakeet-ja": dict(
            repo="csukuangfj/sherpa-onnx-nemo-parakeet-tdt_ctc-0.6b-ja-35000-int8",
            dest="parakeet-ja-0.6b-int8",
            patterns=["*.onnx", "tokens.txt", "test_wavs/*"],
            required=["model.int8.onnx", "tokens.txt"],
            size="约 628MB",
            desc="NVIDIA Parakeet 日语版 0.6B（整句校对，速度快）",
        ),
    }


    def target_dir(name: str) -> Path:
        return MODELS_DIR / MODEL_TARGETS[name]["dest"]


    def is_complete(name: str) -> bool:
        info = MODEL_TARGETS[name]
        d = target_dir(name)
        return d.exists() and all((d / r).exists() for r in info["required"])


    def dir_size(path: Path) -> int:
        return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


    def human(n: float) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024:
                return f"{n:.1f}{unit}"
            n /= 1024
        return f"{n:.1f}TB"


    def download(name: str, on_progress: ProgressCb = None) -> Path:
        """下载某个模型；已完整存在时直接返回。"""
        if name not in MODEL_TARGETS:
            raise KeyError(f"未知模型：{name}")
        dest = target_dir(name)
        if is_complete(name):
            return dest

        from huggingface_hub import snapshot_download
        from tqdm.auto import tqdm

        class _ProgressTqdm(tqdm):  # 把单文件进度透出来
            def update(self, n=1):  # noqa: D102
                r = super().update(n)
                if on_progress is not None:
                    try:
                        on_progress(str(self.desc or ""), int(self.n or 0), int(self.total or 0))
                    except Exception:  # noqa: BLE001
                        pass
                return r

        info = MODEL_TARGETS[name]
        dest.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        snapshot_download(
            repo_id=info["repo"],
            local_dir=str(dest),
            allow_patterns=info["patterns"],
            max_workers=4,
            tqdm_class=_ProgressTqdm,
        )
        if not is_complete(name):
            raise RuntimeError("下载完成但缺少关键文件，请重试")
        (dest / ".complete").write_text(f"{name}\n", encoding="utf-8")
        if on_progress is not None:
            on_progress("完成", int(dir_size(dest)), int(dir_size(dest)))
        _ = t0
        return dest
# END MODULE: jpsub.core.model_catalog

# ======================================================================
# BEGIN MODULE: jpsub.core.pipeline  (jpsub/core/pipeline.py)
# ======================================================================
if False:  # 可阅读的源码区块（独立模块由上方加载器执行）
    # -*- coding: utf-8 -*-
    """主流水线：音频采集 → 静音检测断句 → 流式出字 → 整句高精度校对 → 翻译。"""
    # __FUTURE_IMPORT__ from __future__ import annotations

    import collections
    import queue
    import threading
    import time
    import uuid
    from concurrent.futures import ThreadPoolExecutor, wait

    import numpy as np
    from PySide6 import QtCore

    from ..paths import MODELS
    from .asr import FinalASR
    from .audio import AudioCapture, normalize_gain
    from .segment import Segment
    from .translate import Translator

    # 草稿重识别最多占用这么多比例的墙钟时间，剩下的留给整句校对和翻译；
    # 一句话越长，重识别一次越慢，草稿就会自动跟着放慢（否则会越跑越卡）。
    DRAFT_CPU_BUDGET = 0.5
    # 实时草稿译文每跑 1 秒，至少留这么多秒给整句翻译，避免本地模型被草稿占满。
    LIVE_DUTY_GAP = 1.2



    class _AsrPriorityDispatcher:
        """Parapper-inspired Python ASR scheduler with Final-first FIFO.

        Drafts are disposable. Pending finals are bounded to keep live audio
        responsive if native inference falls behind the capture rate.
        An already running inference is never interrupted.
        """
        def __init__(self, run_final, run_draft, error, *,
                     max_pending=3, max_pending_audio_bytes=8 * 1024 * 1024,
                     max_pending_age_s=30.0):
            self._cv = threading.Condition()
            self._finals = collections.deque()
            self._pending_audio_bytes = 0
            self._max_pending = max(1, int(max_pending))
            self._max_pending_audio_bytes = max(1, int(max_pending_audio_bytes))
            self._max_pending_age_s = max(0.0, float(max_pending_age_s))
            self._draft = None
            self._running = None
            self._closed = False
            self._run_final = run_final
            self._run_draft = run_draft
            self._error = error
            self._thread = threading.Thread(
                target=self._worker, name="yisheng-asr-priority", daemon=True)
            self._thread.start()

        def submit_final(self, seg, audio):
            with self._cv:
                if self._closed:
                    return False
                size = int(audio.nbytes)
                if size > self._max_pending_audio_bytes:
                    return False
                self._discard_expired_locked(time.monotonic())
                while self._finals and (
                    len(self._finals) >= self._max_pending
                    or self._pending_audio_bytes + size > self._max_pending_audio_bytes
                ):
                    _, old_audio, _ = self._finals.popleft()
                    self._pending_audio_bytes -= int(old_audio.nbytes)
                self._finals.append((seg, audio, time.monotonic()))
                self._pending_audio_bytes += size
                self._draft = None
                self._cv.notify()
                return True

        def _discard_expired_locked(self, now):
            while (self._finals and
                   now - self._finals[0][2] > self._max_pending_age_s):
                _, old_audio, _ = self._finals.popleft()
                self._pending_audio_bytes -= int(old_audio.nbytes)

        def submit_draft(self, gen, audio):
            with self._cv:
                if self._closed or self._finals or self._running is not None:
                    return False
                self._draft = (gen, audio)
                self._cv.notify()
                return True

        def has_final_work(self):
            with self._cv:
                return bool(self._finals) or self._running == "final"

        def is_active(self):
            with self._cv:
                return bool(self._finals or self._draft or self._running)

        def clear_draft(self):
            with self._cv:
                self._draft = None

        def _worker(self):
            while True:
                with self._cv:
                    while not self._finals and self._draft is None and not self._closed:
                        self._cv.wait()
                    self._discard_expired_locked(time.monotonic())
                    if self._finals:
                        seg, audio, _ = self._finals.popleft()
                        self._pending_audio_bytes -= int(audio.nbytes)
                        args = (seg, audio)
                        self._running = "final"
                        callback = self._run_final
                    elif self._draft is not None and not self._closed:
                        args = self._draft
                        self._draft = None
                        self._running = "draft"
                        callback = self._run_draft
                    else:
                        if self._closed:
                            break
                        # All queued finals may have expired while native
                        # inference was running. Stay alive for fresh work.
                        continue
                try:
                    callback(*args)
                except Exception as exc:
                    self._error(f"ASR 调度任务异常：{exc}")
                finally:
                    with self._cv:
                        self._running = None
                        self._cv.notify_all()

        def shutdown(self, *, graceful, timeout):
            with self._cv:
                self._closed = True
                self._draft = None
                if not graceful:
                    self._finals.clear()
                    self._pending_audio_bytes = 0
                self._cv.notify_all()
            if self._thread is not threading.current_thread():
                self._thread.join(max(0.0, timeout))
            return not self._thread.is_alive()


    class Pipeline(QtCore.QThread):
        """在后台线程中运行整条识别翻译流水线。"""

        sig_status = QtCore.Signal(str)
        sig_error = QtCore.Signal(str)
        sig_partial = QtCore.Signal(str)             # 流式日语文本（空串=清空）
        sig_segment = QtCore.Signal(object)          # Segment 最终日语
        sig_live_zh = QtCore.Signal(str, str)        # (sid, 实时译文增量后的全文)
        sig_final_zh = QtCore.Signal(str, str)       # (sid, 最终译文)
        sig_translate_info = QtCore.Signal(dict)     # 本次翻译来自哪个服务/耗时
        sig_level = QtCore.Signal(float)             # 0~1 音量
        sig_discontinuity = QtCore.Signal()          # 音频丢帧/暂停恢复：清理旧的实时行
        sig_stats = QtCore.Signal(dict)              # 统计信息

        def __init__(self, config, parent=None):
            super().__init__(parent)
            self.cfg = config
            self._stop = threading.Event()
            self._graceful_stop = False       # 手动停止：排空当前最终识别与翻译
            self._pause = threading.Event()
            self._reset_pending = threading.Event()
            self._queue: queue.Queue = queue.Queue(maxsize=200)
            self._capture: AudioCapture | None = None
            # Native Parakeet is still sherpa-onnx; Python controls priority.
            self._asr_queue = _AsrPriorityDispatcher(
                self._run_final, self._run_draft, self.sig_error.emit)
            self._trans_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="translate")
            self._live_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="translate-live")
            self._pools_closed = False
            self._forced_cancel = threading.Event()
            # Internal safety budgets, not user translation/VAD settings.
            self._graceful_final_timeout = 90.0
            self._graceful_translation_timeout = 180.0
            self._cancel_timeout = 1.0
            self._futures_lock = threading.Lock()
            self._pool_futures = {
                pool: set() for pool in
                (self._trans_pool, self._live_pool)
            }

            # 运行状态
            self._fed = 0                    # 已处理样本数，对齐真实采集时间轴（16k）
            self._received_samples = 0       # 采集端样本位置；排队丢帧也必须前进
            self._received_lock = threading.Lock()
            self._pre_roll: collections.deque = collections.deque(maxlen=18)   # ~0.56s 预卷
            self._raw_frames: collections.deque = collections.deque(maxlen=1250)  # 40 秒原始音频
            self._vad_origin = 0
            self._active = False
            self._utterance: list[np.ndarray] = []
            self._utterance_samples = 0
            self._utterance_start = 0.0
            self._partial = ""
            self._last_final_jp: list[str] = []
            # 只保存有限的去重 ID；不长期保留已完成句子及其译文。
            self._committed_turns: set[str] = set()
            self._committed_turn_order: collections.deque[str] = collections.deque(maxlen=256)
            # final 翻译采用单个 drain worker，待处理任务仅保留最新 N 条。
            self._final_translation_lock = threading.Lock()
            self._final_translation_pending: collections.deque[tuple[str, str, list[str]]] = collections.deque()
            self._final_translation_draining = False
            self._live = {"gen": 0, "sid": "", "busy": False, "last_req": 0.0, "text": "", "latency": 0.0}
            self._fallback_notified = ""
            self._stream = None
            self._draft_engine: FinalASR | None = None
            self._draft_mode = "off"
            self._draft_busy = False
            self._draft_started = 0.0
            self._draft_next_ok = 0.0
            self._final_busy = 0
            self._final: FinalASR | None = None
            self._vad = None
            self._level_counter = 0          # sig_level 降采样计数器
            self._max_segment_samples = 0   # 在 _setup 里初始化，避免热路径每帧读配置
            self._vad_pending = np.zeros(0, dtype=np.float32)
            self._vad_window = 512
            self._queue_warned = False

        # ------------------------------------------------------------- 生命周期
        def _submit(self, pool, fn, *args) -> None:
            """Register each task so shutdown can drain with a real deadline."""
            if self._pools_closed or self._forced_cancel.is_set():
                return
            try:
                future = pool.submit(fn, *args)
            except RuntimeError:  # pool already closed by shutdown
                return
            with self._futures_lock:
                self._pool_futures[pool].add(future)

            def completed(done):
                with self._futures_lock:
                    self._pool_futures[pool].discard(done)

            future.add_done_callback(completed)
            return future

        def has_pending_tasks(self) -> bool:
            """True while a model worker still owns this pipeline's Qt signals."""
            with self._futures_lock:
                return (self._asr_queue.is_active()
                    or any(tasks for tasks in self._pool_futures.values()))

        def cancel_pending(self) -> None:
            """Explicit forced cancellation: running native calls may finish later."""
            self._forced_cancel.set()
            with self._final_translation_lock:
                self._final_translation_pending.clear()
            self._graceful_stop = False
            self._stop.set()
            if self._capture:
                self._capture.stop()
            self._asr_queue.shutdown(graceful=False, timeout=self._cancel_timeout)
            for pool in (self._trans_pool, self._live_pool):
                with self._futures_lock:
                    pending = tuple(self._pool_futures[pool])
                for future in pending:
                    future.cancel()

        def _drain_pool(self, pool, timeout: float, description: str,
                        *, preserve_tasks: bool) -> None:
            """Close submissions, then wait for registered work up to a deadline.

            shutdown(wait=False) alone is NOT the synchronization mechanism.
            The future barrier below is; late native workers are quarantined.
            """
            pool.shutdown(wait=False, cancel_futures=not preserve_tasks)
            with self._futures_lock:
                remaining = tuple(self._pool_futures[pool])
            if remaining:
                _, outstanding = wait(remaining, timeout=max(0.0, timeout))
                if outstanding:
                    self._forced_cancel.set()
                    for future in outstanding:
                        future.cancel()
                    self.sig_error.emit(
                        f"{description}等待超时；已隔离未完成的模型任务，避免旧字幕覆盖新一轮")

        def _shutdown_pools(self) -> None:
            if self._pools_closed:
                return
            graceful = self._graceful_stop and not self._forced_cancel.is_set()
            # Drain all final ASR requests before closing the translation pool.
            drained = self._asr_queue.shutdown(
                graceful=graceful,
                timeout=self._graceful_final_timeout if graceful else self._cancel_timeout)
            if not drained:
                self._forced_cancel.set()
                self.sig_error.emit("最终日语识别等待超时；未完成任务已隔离")
            if graceful and not self._forced_cancel.is_set():
                self._drain_pool(self._trans_pool, self._graceful_translation_timeout,
                                 "最终中文翻译", preserve_tasks=True)
            else:
                self._drain_pool(self._trans_pool, self._cancel_timeout,
                                 "取消翻译任务", preserve_tasks=False)
            self._pools_closed = True
            self._drain_pool(self._live_pool, self._cancel_timeout, "草稿翻译",
                             preserve_tasks=False)

        def _cancel_final(self) -> bool:
            """Normal stop retains the last sentence; force/timeout does not."""
            return self._forced_cancel.is_set() or (self._stop.is_set() and not self._graceful_stop)

        def stop(self, max_wait: float = 1.5, *, graceful: bool = False) -> None:
            """仅手动停止聆听使用 graceful；设置重启/退出继续快速取消。

            停止采集后由流水线线程排空最终识别和翻译；GUI 的等待时间仍有上限。
            """
            self._graceful_stop = graceful
            self._stop.set()
            if self._capture:
                self._capture.stop()
            self.wait(int(max_wait * 1000))

        def pause(self, flag: bool) -> None:
            if flag:
                self._pause.set()
            else:
                self._reset_pending.set()
                self._pause.clear()

        # ------------------------------------------------------------- 主循环
        def run(self) -> None:  # noqa: C901
            try:
                try:
                    self._setup()
                except Exception as e:  # noqa: BLE001
                    self.sig_error.emit(str(e))
                    self.sig_status.emit("启动失败")
                    return

                self.sig_status.emit("正在聆听…")
                while not self._stop.is_set():
                    try:
                        packet = self._queue.get(timeout=0.2)
                        chunk, rms, offset = self._unpack_audio(packet)
                    except queue.Empty:
                        # AudioCapture reports WASAPI failures and returns; no new
                        # packets will arrive. Never leave the UI claiming to listen
                        # while an exited capture thread feeds an empty queue.
                        if (not self._stop.is_set() and self._capture is not None
                                and not self._capture.is_alive()):
                            self.sig_status.emit(
                                "音频采集已停止，请检查或重新选择设备，再点击开始聆听")
                            self.sig_discontinuity.emit()
                            self._stop.set()
                            break
                        continue
                    if self._stop.is_set():
                        break
                    if self._pause.is_set():
                        continue
                    if self._reset_pending.is_set():
                        self._reset_audio_discontinuity(offset)
                    try:
                        self._process_chunk(chunk, rms)
                    except Exception as e:  # noqa: BLE001
                        self.sig_error.emit(f"处理音频出错：{e}")

                if self._graceful_stop and not self._pause.is_set():
                    # 停止采集不代表最后一次录音块已经处理；后台消化已接收的队列，
                    # 然后提交末尾尚未因静音而封句的语音。
                    while True:
                        try:
                            packet = self._queue.get_nowait()
                            chunk, rms, offset = self._unpack_audio(packet)
                        except queue.Empty:
                            break
                        if self._reset_pending.is_set():
                            self._reset_audio_discontinuity(offset)
                        try:
                            self._process_chunk(chunk, rms)
                        except Exception as e:  # noqa: BLE001
                            self.sig_error.emit(f"处理尾部音频出错：{e}")
                    if self._active and self._utterance:
                        self._finalize_utterance()
                self.sig_level.emit(0.0)
            finally:
                if self._capture:
                    self._capture.stop()
                    self._capture.join(timeout=2.0)
                # finished 代表所有模型工作也已结束。
                self._shutdown_pools()

        @staticmethod
        def _unpack_audio(packet):
            # Compatibility with older test/capture producers emitting (chunk, rms).
            return (*packet, None) if len(packet) == 2 else packet

        def _reset_audio_discontinuity(self, sample_start: int | None = None) -> None:
            """Discard old VAD state and advance the clock past missing samples."""
            if sample_start is not None:
                self._fed = max(self._fed, sample_start)
            self._reset_pending.clear()
            self._pre_roll.clear()
            self._active = False
            self._utterance = []
            self._utterance_samples = 0
            self._partial = ""
            self._draft_next_ok = 0.0
            self._draft_busy = False
            self._asr_queue.clear_draft()
            self._vad_pending = np.zeros(0, dtype=np.float32)
            self._vad.reset()
            self._vad_origin = self._fed
            self._raw_frames.clear()
            self._live['gen'] += 1
            self._live.update(sid="", busy=False, text="", last_req=0.0)
            if self._stream:
                self._stream.reset()
            self.sig_discontinuity.emit()

        # ------------------------------------------------------------- 初始化
        def _setup(self) -> None:
            cfg = self.cfg
            # 0) 先定下整句校对引擎：草稿要不要和它共用同一份模型实例，取决于这里
            engine = "parakeet"
            cloud = {}
            if not FinalASR.available(engine):
                raise FileNotFoundError("日语识别模型不完整，请重新安装软件")
            final_threads = int(cfg.get("asr.final_threads", 6))
            # 1) 实时出字：用唯一模型滚动识别
            want_mode = str(cfg.get("asr.draft_mode", "rolling"))
            if not bool(cfg.get("asr.partial", True)):
                want_mode = "off"
            self._draft_mode = "off"
            if want_mode != "off":
                self.sig_status.emit("正在加载日语识别模型…")
                # 草稿和整句校对共用唯一模型和原生服务进程。
                self._draft_engine = FinalASR("parakeet", num_threads=final_threads)
                self._draft_engine.load()
                self._draft_mode = "rolling"
            # 2) 静音检测
            import sherpa_onnx

            vad_path = MODELS / "silero_vad.onnx"
            if not vad_path.exists():
                raise FileNotFoundError("缺少 silero_vad.onnx，请先运行 scripts/download_models.py")
            vcfg = sherpa_onnx.VadModelConfig()
            vcfg.silero_vad.model = str(vad_path)
            vcfg.silero_vad.window_size = self._vad_window
            vcfg.silero_vad.threshold = float(cfg.get("vad.threshold", 0.5))
            vcfg.silero_vad.min_silence_duration = int(cfg.get("vad.min_silence_ms", 350)) / 1000.0
            vcfg.silero_vad.min_speech_duration = int(cfg.get("vad.min_speech_ms", 200)) / 1000.0
            vcfg.silero_vad.max_speech_duration = float(cfg.get("asr.max_segment_s", 24))
            vcfg.sample_rate = 16000
            vcfg.num_threads = 1
            self._vad = sherpa_onnx.VoiceActivityDetector(vcfg, buffer_size_in_seconds=60)
            # 3) 整句校对引擎（异步预加载）
            if (self._draft_mode == "rolling" and self._draft_engine is not None
                    and self._same_engine(self._draft_engine.engine, engine)):
                # 共用上面已经加载好的那一份（草稿 ≠ 校对只是两个用途，模型是同一个）
                self._final = self._draft_engine
            else:
                self._final = FinalASR(engine, num_threads=final_threads, cloud=cloud)
            self._preload_final()
            if self._stop.is_set():
                return
            if cfg.get("translate.enabled", True) and cfg.get("translate.provider", "") == "llamacpp":
                self.sig_status.emit("正在加载本地翻译模型…")
                self._warmup_translate()
                if self._stop.is_set():
                    return
            # 4) 音频采集
            self.sig_status.emit("正在打开音频设备…")
            self._capture = AudioCapture(
                source=str(cfg.get("audio.source", "loopback")),
                device_name=str(cfg.get("audio.device", "") or ""),
                on_chunk=self._on_audio,
                on_error=lambda m: self.sig_error.emit(m),
                block_ms=int(cfg.get("audio.block_ms", 80)),
                on_status=lambda m: self.sig_status.emit(m),
            )
            # The capture callback may run immediately; never reset its clock afterwards.
            self._fed = 0
            with self._received_lock:
                self._received_samples = 0
            self._capture.start()
            # Independent Python safeguard if native VAD fails to terminate
            # an unusually long speech segment; measured in 16 kHz samples.
            self._max_segment_samples = max(
                self._vad_window, int(float(cfg.get("asr.max_segment_s", 24)) * 16000))

        @staticmethod
        def _same_engine(a: str, b: str) -> bool:
            """两个角色能不能共用同一份模型实例：同名、而且是 sherpa 系离线模型才行。"""
            if a != b:
                return False
            from .config import FINAL_ENGINES

            return str(FINAL_ENGINES.get(b, {}).get("kind") or "sherpa") in ("sherpa", "native")

        def _preload_final(self) -> None:
            try:
                self._final.load()
                self.sig_status.emit("模型就绪，正在聆听…")
            except Exception as e:  # noqa: BLE001
                self.sig_error.emit(f"校对模型加载失败：{e}")
                raise

        # ------------------------------------------------------------- 音频处理
        def _on_audio(self, chunk: np.ndarray, rms: float) -> None:
            with self._received_lock:
                offset = self._received_samples
                self._received_samples += int(chunk.size)
            packet = (chunk, rms, offset)
            try:
                self._queue.put_nowait(packet)
            except queue.Full:
                # 既然已经丢了一帧，剩余旧音频就不能再与新块拼接成连续语音。
                # 保留最新块，从下一帧起重置 VAD；避免处理几秒前的积压字幕。
                self._reset_pending.set()
                while True:
                    try:
                        self._queue.get_nowait()
                    except queue.Empty:
                        break
                try:
                    self._queue.put_nowait(packet)
                except queue.Full:
                    pass  # 消费线程并发不影响重置；下一次新块还会继续到达。
                if not self._queue_warned:
                    self._queue_warned = True
                    self.sig_error.emit("音频处理跟不上播放速度，已丢弃积压音频并重置分段")

        def _process_chunk(self, chunk: np.ndarray, rms: float) -> None:
            level = min(1.0, max(0.0, (20 * np.log10(rms + 1e-6) + 60) / 60)) if rms > 1e-6 else 0.0
            self._level_counter += 1
            if self._level_counter % 4 == 0:
                self.sig_level.emit(level)
            self._vad_pending = np.concatenate((self._vad_pending, chunk))
            while self._vad_pending.size >= self._vad_window:
                frame = self._vad_pending[:self._vad_window]
                self._vad_pending = self._vad_pending[self._vad_window:]
                self._process_frame(frame)

        def _process_frame(self, frame: np.ndarray) -> None:
            now = time.time()
            self._fed += frame.size
            self._raw_frames.append(frame.copy())
            # VAD 以固定窗口运行。整句必须使用 VAD 保存的音频，不能把队列直接 pop 掉。
            self._vad.accept_waveform(normalize_gain(frame, max_gain=6.0))
            speech = bool(self._vad.is_speech_detected())
            if speech and not self._active:
                self._active = True
                self._utterance = list(self._pre_roll)
                self._utterance_samples = sum(c.size for c in self._pre_roll)
                self._utterance_start = (self._fed - frame.size - sum(c.size for c in self._pre_roll)) / 16000
                self._live['gen'] += 1
                self._live.update(sid=f"L{self._live['gen']}", busy=False, last_req=0.0, text='')
                self._draft_next_ok = now + int(self.cfg.get('asr.draft_interval_ms', 900)) / 1000
            if self._active:
                self._utterance.append(frame)
                self._utterance_samples += frame.size
            self._pre_roll.append(frame)
            if self._draft_mode == 'streaming' and self._stream is not None:
                text = self._stream.feed(frame)
                if text is not None and text != self._partial:
                    self._partial = text
                    self.sig_partial.emit(text)
                    self._maybe_live_translate(now)
            while not self._vad.empty():
                segment = self._vad.front
                # VAD 接收的逐帧增益音频只用于检测；识别必须使用原始录音。
                # 否则每 32ms 一次的独立放大会改变音色，并放大停顿里的背景噪声。
                history = np.concatenate(self._raw_frames)
                history_start = self._fed - history.size
                segment_start = self._vad_origin + segment.start
                begin = max(history_start, segment_start - 6400)
                end = min(self._fed, segment_start + len(segment.samples) + 2560)
                audio = history[begin-history_start:end-history_start].copy()
                start = begin / 16000.0
                self._vad.pop()
                self._finalize_utterance(audio=audio, start=start)
            if (self._active and self._max_segment_samples > 0
                    and self._utterance_samples >= self._max_segment_samples):
                # Native VAD should normally split first. If it doesn't,
                # finalize the bounded Python audio and reset the VAD origin
                # so it cannot later replay the same long speech segment.
                self._finalize_utterance()
                self._vad.reset()
                self._vad_origin = self._fed
                self._pre_roll.clear()
                self._raw_frames.clear()
            if self._active:
                self._maybe_rolling_draft(now)

        def _finalize_utterance(self, keep_active: bool = False,
                                audio: np.ndarray | None = None, start: float | None = None) -> None:
            if audio is None:
                audio = np.concatenate(self._utterance) if self._utterance else np.zeros(0, dtype=np.float32)
            live_text = self._partial
            self._utterance = []
            self._utterance_samples = 0
            self._active = keep_active
            self._partial = ''
            self._live['gen'] += 1  # 已结束句子的慢草稿不能在最终结果之后重新冒出来
            self.sig_partial.emit('')
            self._draft_next_ok = 0.0
            # Final turn supersedes stale interim audio.
            self._asr_queue.clear_draft()
            self._draft_busy = False
            if self._stream is not None:
                self._stream.reset()
            if audio.size < 4000 or self._cancel_final():
                return
            t0 = self._utterance_start if start is None else start
            seg = Segment(sid=uuid.uuid4().hex[:8], jp='', t0=t0,
                          t1=t0 + audio.size / 16000.0, live_jp=live_text)
            if not self._asr_queue.submit_final(seg, audio) and not self._cancel_final():
                self.sig_error.emit("最终 ASR 队列已关闭或音频片段过大，已跳过本句")

        def _run_final(self, seg: Segment, audio: np.ndarray) -> None:
            if self._cancel_final():
                return
            self._final_busy += 1
            try:
                try:
                    context = ("\n".join(self._last_final_jp[-3:])
                               if self.cfg.get("asr.context_prompt", True) else "")
                    result = self._final.transcribe(audio, context)
                except Exception as e:  # noqa: BLE001
                    if not self._cancel_final():
                        self.sig_error.emit(f"整句识别失败：{e}")
                    return
                self._emit_final(seg, result)
            finally:
                self._final_busy -= 1

        def _emit_final(self, seg: Segment, result) -> None:
            text = result.text.strip()
            if self._cancel_final():
                return
            if not text:
                self.sig_partial.emit("")
                return
            # Emit one immutable completion per Turn; never repeat translation.
            if seg.sid in self._committed_turns:
                return
            if len(self._committed_turn_order) == self._committed_turn_order.maxlen:
                self._committed_turns.discard(self._committed_turn_order.popleft())
            self._committed_turn_order.append(seg.sid)
            self._committed_turns.add(seg.sid)
            seg.jp = text
            seg.asr_seconds = result.seconds
            seg.rtf = result.rtf
            context = self._context_lines()
            self._last_final_jp.append(text)
            # 上下文中保留的日语文本也不能超出用户设置的字幕数量。
            keep = max(1, min(1000, int(self.cfg.get("ui.history_limit", 3))))
            if len(self._last_final_jp) > keep:
                self._last_final_jp = self._last_final_jp[-keep:]
            self.sig_segment.emit(seg)
            self.sig_stats.emit({"rtf": round(result.rtf, 2), "asr_ms": int(result.seconds * 1000),
                                 "audio_s": round(result.audio_seconds, 1)})
            if self.cfg.get("translate.enabled", True):
                sid = seg.sid
                self._queue_final_translation(sid, text, context)

        # ------------------------------------------------------------- 滚动草稿
        def _maybe_rolling_draft(self, now: float) -> None:
            if (self._draft_mode != "rolling" or self._draft_engine is None or self._draft_busy
                    or self._pause.is_set() or self._stop.is_set()):
                return
            if self._final_busy or self._asr_queue.has_final_work():
                return          # Queued/active Final must take priority.
            if now < self._draft_next_ok:
                return
            total = sum(len(c) for c in self._utterance)
            if total < int(16000 * 0.7):
                return
            self._draft_busy = True
            self._draft_started = now
            gen = self._live["gen"]
            audio = np.concatenate(self._utterance)
            if not self._asr_queue.submit_draft(gen, audio):
                self._draft_busy = False

        def _run_draft(self, gen: int, audio: np.ndarray) -> None:
            text = ""
            try:
                result = self._draft_engine.transcribe(audio)
                text = result.text.strip()
            except Exception:  # noqa: BLE001
                text = ""
            finally:
                self._draft_busy = False
                # 旧句草稿可能在下一句话开始之后才完成，不能再改写新句的调度时刻。
                if gen == self._live["gen"]:
                    spent = max(0.0, time.time() - self._draft_started)
                    interval = int(self.cfg.get("asr.draft_interval_ms", 600)) / 1000.0
                    self._draft_next_ok = self._draft_started + max(interval, spent / DRAFT_CPU_BUDGET)
            if (not text or gen != self._live["gen"] or not self._active or self._final_busy
                    or self._pause.is_set() or self._stop.is_set()):
                return
            if text != self._partial:
                self._partial = text
                self.sig_partial.emit(text)
                self._maybe_live_translate(time.time())

        # ------------------------------------------------------------- 翻译
        def _context_lines(self) -> list[str]:
            n = int(self.cfg.get("translate.context_lines", 3))
            return self._last_final_jp[-n:] if n > 0 else []

        def _warmup_translate(self) -> None:
            """启动时静默预热翻译服务（本地大模型先加载好，第一句就不用等）。"""
            try:
                Translator(self.cfg).translate("こんにちは。", [])
            except Exception:  # noqa: BLE001
                pass

        def _retained_caption_limit(self) -> int:
            return max(1, min(1000, int(self.cfg.get("ui.history_limit", 3))))

        def trim_pending_translations(self) -> None:
            """修改保留数量后立即清理多余的待翻译文本。调用方可以是 GUI 线程。"""
            with self._final_translation_lock:
                keep = self._retained_caption_limit()
                while len(self._final_translation_pending) > keep:
                    self._final_translation_pending.popleft()

        def _queue_final_translation(self, sid: str, text: str, context: list[str]) -> None:
            if self._forced_cancel.is_set() or self._pools_closed:
                return
            with self._final_translation_lock:
                self._final_translation_pending.append((sid, text, context))
                keep = self._retained_caption_limit()
                while len(self._final_translation_pending) > keep:
                    self._final_translation_pending.popleft()
                if self._final_translation_draining:
                    return
                self._final_translation_draining = True
            if self._submit(self._trans_pool, self._drain_final_translations) is None:
                with self._final_translation_lock:
                    self._final_translation_pending.clear()
                    self._final_translation_draining = False

        def _drain_final_translations(self) -> None:
            while True:
                with self._final_translation_lock:
                    if self._forced_cancel.is_set():
                        self._final_translation_pending.clear()
                        self._final_translation_draining = False
                        return
                    keep = self._retained_caption_limit()
                    while len(self._final_translation_pending) > keep:
                        self._final_translation_pending.popleft()
                    if not self._final_translation_pending:
                        self._final_translation_draining = False
                        return
                    item = self._final_translation_pending.popleft()
                try:
                    self._run_translate_final(*item)
                except Exception as exc:  # noqa: BLE001 不允许一次异常永久卡住后续译文
                    self.sig_error.emit(f"最终翻译任务异常：{exc}")

        def _run_translate_final(self, sid: str, text: str, context: list[str] | None = None) -> None:
            if self._cancel_final():
                return
            translator = Translator(self.cfg)
            t0 = time.time()
            try:
                parts = []
                last_emit = [0.0]
                last_text = [""]
                def delta(piece):
                    if not piece:
                        return
                    parts.append(piece)
                    now = time.monotonic()
                    # 设置页可调。40ms 默认值保留旧版输出速度，修改即时生效。
                    interval = max(20, int(self.cfg.get("translate.final_stream_interval_ms", 40))) / 1000.0
                    current = ''.join(parts)
                    if (not self._cancel_final() and current != last_text[0]
                            and now-last_emit[0] >= interval):
                        self.sig_final_zh.emit(sid, current)
                        last_text[0] = current
                        last_emit[0] = now
                out = translator.translate(text, context or [], on_delta=delta)
            except Exception as e:  # noqa: BLE001
                # 输出流中断时撤回未完成字幕（也清除此前的草稿预览）。
                if not self._cancel_final():
                    self.sig_final_zh.emit(sid, "")
                    self.sig_error.emit(f"翻译失败：{e}")
                return
            if self._cancel_final():
                return
            if out != last_text[0]:
                self.sig_final_zh.emit(sid, out)
            from .config import TRANSLATE_PRESETS

            label = TRANSLATE_PRESETS.get(translator.last_provider, {}).get("label", translator.last_provider)
            self.sig_translate_info.emit({
                "provider": translator.last_provider,
                "label": label,
                "seconds": round(time.time() - t0, 1),
            })
            chosen = str(self.cfg.get("translate.provider", ""))
            if (translator.last_provider and translator.last_provider != chosen
                    and self._fallback_notified != chosen):
                self._fallback_notified = chosen
                a = TRANSLATE_PRESETS.get(chosen, {}).get("label", chosen)
                b = TRANSLATE_PRESETS.get(translator.last_provider, {}).get("label", translator.last_provider)
                why = str(translator.last_reason or "")
                why = f"（{why[:48]}）" if why else ""
                self.sig_status.emit(f"「{a}」不可用{why}，已自动降级到「{b}」")

        def _maybe_live_translate(self, now: float) -> None:
            if (self._pause.is_set() or self._stop.is_set()
                    or not self.cfg.get("translate.live", True)
                    or not self.cfg.get("translate.enabled", True)):
                return
            live = self._live
            interval = int(self.cfg.get("translate.live_min_interval_ms", 1100)) / 1000.0
            min_new = int(self.cfg.get("translate.live_min_new_chars", 2))
            text = self._partial.strip()
            if not text or live["busy"]:
                return
            if len(text) < 6:
                return  # 太短的草稿容易翻出乱码，等积累一点再翻
            if len(text) - len(live["text"]) < min_new:
                return
            # 实测的翻译耗时决定节奏：本地模型一句要 2 秒，那就至少隔 2.4 秒再发下一句，
            # 否则草稿翻译会把本地模型（和 CPU）排满，整句翻译只能排队等 —— 越看越卡。
            gap = max(interval, float(live.get("latency") or 0.0) * LIVE_DUTY_GAP)
            if now - live["last_req"] < gap:
                return
            live["busy"] = True
            live["last_req"] = now
            live["text"] = text
            gen = live["gen"]
            sid = live["sid"]
            self._submit(self._live_pool, self._run_translate_live, gen, sid, text)

        def _live_provider(self) -> str:
            """草稿只使用当前选择的翻译服务，避免调用已删除的本地引擎。"""
            return str(self.cfg.get("translate.provider", "llamacpp"))

        def _run_translate_live(self, gen: int, sid: str, text: str) -> None:
            if self._stop.is_set():
                return
            translator = Translator(self.cfg)
            t0 = time.time()
            out = ""
            ran = False
            preview_emitted = [False]
            last_preview = [None]
            try:
                # 句子已经说完了（或在停止/暂停中）就别再翻了：这一趟的结果没人要，
                # 白白占着本地模型，还会让界面冒出一行过期的译文。
                if (gen == self._live["gen"] and self._active and not self._stop.is_set()
                        and not self._pause.is_set()):
                    ran = True
                    parts = []
                    last_emit = [0.0]
                    def delta(piece):
                        if not piece:
                            return  # 空增量不是“清空字幕”事件，不应触发一次可见闪烁。
                        parts.append(piece)
                        now = time.monotonic()
                        full = ''.join(parts)
                        if (gen == self._live['gen'] and self._active and not self._stop.is_set()
                                and not self._pause.is_set()
                                and full != last_preview[0] and now-last_emit[0] >= 0.04):
                            self.sig_live_zh.emit(sid, full)
                            preview_emitted[0] = True
                            last_preview[0] = full
                            last_emit[0] = now
                    out = translator.translate(text, self._context_lines(),
                                               provider=self._live_provider(), on_delta=delta)
            except Exception:  # noqa: BLE001 实时翻译失败不打断主流程
                # 只撤回本次已经显示的失败增量；不要清掉上一条有效预览。
                if (preview_emitted[0] and gen == self._live["gen"]
                        and self._active and not self._stop.is_set()
                        and not self._pause.is_set()):
                    self.sig_live_zh.emit(sid, "")
                    preview_emitted[0] = False  # 清空已发送，无需在空结果路径重复清理。
                out = ""
            finally:
                if gen == self._live["gen"]:
                    self._live["busy"] = False
                if ran and gen == self._live["gen"]:
                    # 过期请求不能改变新句的自适应翻译间隔。
                    spent = max(0.0, time.time() - t0)
                    old = float(self._live.get("latency") or 0.0)
                    self._live["latency"] = spent if old <= 0 else round(old * 0.6 + spent * 0.4, 3)
            if not out and preview_emitted[0]:
                # 没有抛错但结果为空的调用，同样不能遗留此前显示的半句预览。
                if (gen == self._live["gen"] and self._active and not self._stop.is_set()
                        and not self._pause.is_set()):
                    self.sig_live_zh.emit(sid, "")
            if out and (out.count("*") >= 4 or "＊" * 2 in out):
                # 模型最后确认是乱码时，撤回已经展示出来的错误增量。
                if (preview_emitted[0] and gen == self._live["gen"]
                        and self._active and not self._stop.is_set()
                        and not self._pause.is_set()):
                    self.sig_live_zh.emit(sid, "")
                out = ""
            if (gen == self._live["gen"] and out and self._active and not self._stop.is_set()
                    and not self._pause.is_set()):
                if out != last_preview[0]:
                    self.sig_live_zh.emit(sid, out)
                from .config import TRANSLATE_PRESETS

                label = TRANSLATE_PRESETS.get(translator.last_provider, {}).get("label", translator.last_provider)
                self.sig_translate_info.emit({
                    "provider": translator.last_provider, "label": label,
                    "seconds": round(time.time() - t0, 1), "live": True,
                })
# END MODULE: jpsub.core.pipeline

# ======================================================================
# BEGIN MODULE: jpsub.core.segment  (jpsub/core/segment.py)
# ======================================================================
if False:  # 可阅读的源码区块（独立模块由上方加载器执行）
    # -*- coding: utf-8 -*-
    """字幕句（Segment）。

    单独放在这里，是为了让界面模块（transcript/window）不必为了一个数据类去导入
    识别、翻译那些重型依赖——那样会让软件启动慢好几秒。
    """
    # __FUTURE_IMPORT__ from __future__ import annotations

    from dataclasses import dataclass


    @dataclass
    class Segment:
        sid: str
        jp: str
        zh: str = ""
        t0: float = 0.0          # 相对会话开始的秒数
        t1: float = 0.0
        rtf: float = 0.0
        asr_seconds: float = 0.0
        provider: str = ""
        live_jp: str = ""        # 流式引擎当时的草稿（用于对比）
        done: bool = False
# END MODULE: jpsub.core.segment

# ======================================================================
# BEGIN MODULE: jpsub.core.translate  (jpsub/core/translate.py)
# ======================================================================
if False:  # 可阅读的源码区块（独立模块由上方加载器执行）
    # -*- coding: utf-8 -*-
    """日语→中文：混元 Hy-MT2 7B、微软免费和谷歌免费。"""
    # __FUTURE_IMPORT__ from __future__ import annotations

    import json
    import time
    from typing import Callable, Iterable, Optional

    import httpx

    from .http_util import make_client

    OnDelta = Optional[Callable[[str], None]]

    def _friendly_http_error(e: Exception) -> str:
        if isinstance(e, httpx.HTTPStatusError):
            code = e.response.status_code
            detail = ""
            try:
                body = e.response.json()
                detail = str(body.get("error", {}).get("message") or body.get("message") or "")[:120]
            except Exception:  # noqa: BLE001
                detail = (e.response.text or "")[:120]
            hints = {
                401: "API Key 无效或未填写",
                403: "没有权限或地区受限",
                404: "接口地址或模型名不对",
                429: "请求太频繁或额度用尽",
                500: "服务端出错", 502: "网关错误", 503: "服务暂时不可用",
            }
            return f"{hints.get(code, f'HTTP {code}')}" + (f"（{detail}）" if detail else "")
        if isinstance(e, httpx.TimeoutException):
            return "请求超时（网络不通或被墙）"
        if isinstance(e, httpx.ConnectError):
            url = ""
            try:
                url = str(e.request.url)
            except Exception:  # noqa: BLE001
                pass
            if "127.0.0.1" in url or "localhost" in url:
                return "本地翻译引擎未启动"
            return "无法连接服务器（检查网络/代理）"
        return str(e)[:160]
    class LlamaCppProvider:
        """内置 llama.cpp 引擎（llama-server）：本地、免安装、加载 GGUF 模型。"""

        kind = "llamacpp"

        def __init__(self, service: dict):
            self.service = service or {}

        def translate(self, text: str, context: list[str], glossary, on_delta: OnDelta = None) -> str:
            from .llama_engine import ensure_running, resolve_model

            model = resolve_model(str(self.service.get("model") or ""))
            if model is None:
                raise RuntimeError("尚未选择 GGUF 模型（设置 → 翻译服务 → 本地·内置引擎）")
            variant = str(self.service.get("variant") or "cpu")
            from . import llama_engine as _le

            if not _le.installed(variant) and _le.installed("cpu"):
                variant = "cpu"  # 首选版本未安装时自动回退
            try:
                base = ensure_running(model, variant)
            except Exception:
                if variant == "cpu" or not _le.installed("cpu"):
                    raise
                # 显卡驱动/CUDA/Vulkan 不兼容时继续使用随附 CPU 引擎。
                base = ensure_running(model, "cpu")
            from .llama_engine import RECOMMENDED_MODELS
            if model.name != RECOMMENDED_MODELS[0]["name"]:
                raise RuntimeError("只允许使用混元 Hy-MT2 7B 模型")
            return HyMT2(base).translate(text, context, glossary, on_delta)


    # ---------------------------------------------------------------------------
    class _StreamingLlamaBackend:
        """通过 GGUF 内置模板调用 TranslateGemma 的官方翻译协议。"""
        def __init__(self, base: str):
            self.base = base.removesuffix('/v1')

        def sampling(self):
            return {'temperature': 0.0}

        def translate(self, text, context, glossary, on_delta=None):
            # 模型 GGUF 自带的 chat_template 只在收到这一格式时才会生成训练时使用的
            # “Japanese -> Chinese”专用提示。旧代码手工拼模板，还额外重复了 BOS，
            # llama.cpp 会明确报警并降低短句翻译的稳定性。
            _ = context, glossary
            payload = {
                'messages': self.messages(text, context, glossary),
                'max_tokens': 512,
                'stream': True,
                **self.sampling(),
            }
            parts = []
            with make_client(self.base, timeout=90) as client:
                with client.stream('POST', self.base + '/v1/chat/completions', json=payload) as response:
                    if response.status_code >= 400:
                        response.read()
                        response.raise_for_status()
                    for line in response.iter_lines():
                        if not line.startswith('data:'):
                            continue
                        data = line[5:].strip()
                        if data == '[DONE]':
                            break
                        obj = json.loads(data)
                        if obj.get('error'):
                            raise RuntimeError(str(obj['error']))
                        choices = obj.get('choices') or []
                        piece = str((choices[0].get('delta') or {}).get('content') or '') if choices else ''
                        if piece:
                            parts.append(piece)
                            if on_delta:
                                on_delta(piece)
            out = ''.join(parts).strip()
            if not out:
                raise RuntimeError('本地翻译模型未返回译文')
            return out


    class HyMT2(_StreamingLlamaBackend):
        """腾讯翻译专用模型：用内置聊天模板，支持术语、背景和口语风格。"""

        def messages(self, text, context, glossary):
            sections = []
            terms = [f'{a} 翻译成 {b}' for a, b in glossary if a and b]
            if terms:
                sections.append('参考下面的翻译：\n' + '\n'.join(terms[:40]))
            background = [str(c).strip() for c in context if c]
            if background:
                sections.append('【背景信息，仅供理解，不要翻译】\n' + '\n'.join(background[-8:])[-240:])
            sections.append(
                '将下面日语翻译成自然、简洁的现代汉语口语字幕。只翻译已经说出的内容，'
                '原句没说完时保留未完成的语气，不猜测后半句；保留时态、否定、疑问和人称，'
                '不要把叙述改成劝告。原文省略主语时，不擅自补出“我”或“你”。'
                '不使用文言文或古风措辞，不扩写，不解释。'
                '背景信息只用于理解指代，绝不混入本次译文。只输出译文：\n\n'
                + text
            )
            return [{'role': 'user', 'content': '\n\n'.join(sections)}]


    class GoogleFree:
        kind = "googlefree"
        _URL = "https://translate.googleapis.com/translate_a/single"

        def __init__(self, timeout: float = 8.0):
            self.timeout = timeout

        def translate(self, text: str, context: list[str], glossary, on_delta: OnDelta = None) -> str:  # noqa: ARG002
            params = {"client": "gtx", "sl": "ja", "tl": "zh-CN", "dt": "t", "q": text}
            with httpx.Client(timeout=self.timeout) as client:
                r = client.get(self._URL, params=params)
                r.raise_for_status()
                data = r.json()
            return "".join(seg[0] for seg in data[0] if seg and seg[0]).strip()


    class MicrosoftFree:
        """Edge 136+ 翻译端点；无需旧版 /translate/auth 令牌。"""
        kind = "msfree"
        _API = "https://edge.microsoft.com/translate/translatetext"

        def __init__(self, timeout: float = 8.0):
            self.timeout = timeout

        def translate(self, text: str, context: list[str], glossary, on_delta: OnDelta = None) -> str:  # noqa: ARG002
            params = {"from": "ja", "to": "zh-Hans", "isEnterpriseClient": "false"}
            headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(self._API, params=params, headers=headers, json=[text])
                r.raise_for_status()
                return r.json()[0]["translations"][0]["text"].strip()


    FALLBACK_ORDER = ["ms-free", "google-free"]

    # 翻译服务实例缓存（避免每次翻译都重新构造 provider 对象）
    # key: provider_id -> (provider实例, 构造时使用的 service_dict 哈希)
    import hashlib as _hashlib
    _PROVIDER_CACHE: dict[str, tuple[object, str]] = {}
    _PROVIDER_CACHE_LOCK = __import__("threading").Lock()


    def _service_sig(svc: dict) -> str:
        """把 service dict 的关键字段变成一个字符串签名，用于缓存失效判断。"""
        key = f"{svc.get('kind')}|{svc.get('base_url')}|{svc.get('api_key')}|{svc.get('model')}|{svc.get('variant')}"
        return key


    def get_cached_provider(provider_id: str, svc: dict):
        """获取或新建翻译 provider 实例（线程安全，同一配置只构造一次）。"""
        sig = _service_sig(svc)
        with _PROVIDER_CACHE_LOCK:
            cached = _PROVIDER_CACHE.get(provider_id)
            if cached is not None and cached[1] == sig:
                return cached[0]
            inst = make_provider(svc)
            _PROVIDER_CACHE[provider_id] = (inst, sig)
            return inst


    def make_provider(service: dict):
        kind = service.get("kind")
        if kind == "llamacpp":
            return LlamaCppProvider(service)
        if kind == "msfree":
            return MicrosoftFree()
        if kind == "googlefree":
            return GoogleFree()
        raise RuntimeError(f"未知的翻译服务类型：{kind}")


    class Translator:
        """主服务失败时按微软→谷歌顺序尝试备用服务。"""

        def __init__(self, config):
            self.config = config
            self.last_provider = ""
            self.last_error = ""
            self.last_reason = ""     # 主服务被跳过/失败的原因（降级时给用户看）

        def _service(self, provider: str | None = None) -> dict:
            pid = provider or self.config.get("translate.provider", "llamacpp")
            svc = self.config.service(pid)
            if svc.get("kind") == "llamacpp":
                # 内置引擎要知道用哪个变体（CPU / Vulkan / CUDA）——以前这里漏了，
                # 导致不管设置里选什么都只会用 CPU 引擎
                from .llama_engine import preferred_variant

                svc["variant"] = preferred_variant(self.config)
            return svc

        def _skip_reason(self, svc: dict) -> str | None:
            if svc.get("kind") == "llamacpp":
                from .llama_engine import installed_variants, resolve_model
                if not installed_variants():
                    return "混元翻译引擎尚未下载（请在设置中下载 CPU/Vulkan/CUDA 引擎）"
                if resolve_model(svc.get("model", "") or "") is None:
                    return "混元 Hy-MT2 7B 模型尚未下载（请在设置中下载）"
            return None

        def _fallback_keyless(self, provider: str, text: str, context: list[str],
                              glossary) -> tuple[str, str, list[str]]:
            errors = []
            for pid in FALLBACK_ORDER:
                if pid == provider:
                    continue
                svc = self._service(pid)
                try:
                    out = get_cached_provider(pid, svc).translate(text, context, glossary)
                    if out and out.strip():
                        return pid, out, errors
                    raise RuntimeError("翻译服务返回空内容")
                except Exception as e:
                    errors.append(f"{svc.get('label', pid)}：{_friendly_http_error(e)}")
            return "", "", errors

        def translate(self, text: str, context: list[str], on_delta: OnDelta = None,
                      provider: str | None = None) -> str:
            """翻译文本；主服务失败或未就绪时自动改用免密钥通道。

            provider 参数可临时指定本次使用的服务（例如草稿译文走极速模型）。
            """
            text = (text or "").strip()
            if not text:
                return ""
            glossary = [tuple(x) for x in (self.config.get("translate.glossary", []) or [])]
            provider = provider or self.config.get("translate.provider", "llamacpp")
            errors: list[str] = []

            self.last_reason = ""
            svc = self._service(provider)
            reason = self._skip_reason(svc)
            if reason:
                errors.append(reason)
            else:
                try:
                    out = get_cached_provider(provider, svc).translate(text, context, glossary, on_delta)
                    if not out or not out.strip():
                        raise RuntimeError("翻译服务返回空内容")
                    self.last_provider = provider
                    self.last_error = ""
                    return out
                except Exception as e:  # noqa: BLE001
                    errors.append(f"{svc.get('label', provider)}：{_friendly_http_error(e)}")

            self.last_reason = errors[0] if errors else ""
            if not self.config.get("translate.auto_fallback", False):
                self.last_error = "；".join(errors)
                raise RuntimeError(self.last_error)
            pid, out, errs = self._fallback_keyless(provider, text, context, glossary)
            errors.extend(errs)
            if out:
                self.last_provider = pid
                self.last_error = ""
                return out
            self.last_error = "；".join(errors) or "没有可用的翻译服务"
            raise RuntimeError(self.last_error)

        def test(self, provider: Optional[str] = None) -> str:
            """测试某个服务是否可用，返回中文结果说明。"""
            svc = self._service(provider)
            try:
                out = make_provider(svc).translate("こんにちは、テストです。", [], [])
                return f"连接成功：{out}"
            except Exception as e:  # noqa: BLE001
                return f"连接失败：{_friendly_http_error(e)}"

# END MODULE: jpsub.core.translate

# ======================================================================
# BEGIN MODULE: jpsub.main  (jpsub/main.py)
# ======================================================================
if False:  # 可阅读的源码区块（独立模块由上方加载器执行）
    # -*- coding: utf-8 -*-
    """程序入口：python -m jpsub.main"""
    # __FUTURE_IMPORT__ from __future__ import annotations

    import argparse
    import ctypes
    import sys
    import time
    import traceback
    from pathlib import Path

    from PySide6 import QtCore, QtGui, QtWidgets

    from . import APP_NAME, __version__
    from .core.config import Config
    from .paths import ASSETS, CONFIG_PATH, LOG_PATH, ensure_dirs

    MUTEX_NAME = "Local\\jpsub_translate_single_instance"
    ERROR_ALREADY_EXISTS = 183
    SW_RESTORE = 9
    RDW_INVALIDATE = 0x0001
    RDW_ALLCHILDREN = 0x0080
    RDW_UPDATENOW = 0x0100
    WAIT_EXISTING_WINDOW_S = 4.0   # 已有实例还在加载时，等它把窗口显示出来的最长时间

    _MUTEX_HANDLE = None           # 进程存活期间一直持有，互斥体才不会提前消失
    _T_START = time.perf_counter()


    def _log(msg: str) -> None:
        """追加一行启动日志（排错用），失败也不影响使用。"""
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                        f"+{time.perf_counter() - _T_START:5.2f}s  {msg}\n")
        except Exception:  # noqa: BLE001
            pass


    def _existing_window() -> tuple[str, int]:
        """单实例检测。

        ("new", 0)       —— 没有别的实例，正常启动。
        ("existing", hwnd) —— 已有实例在运行，这是它的主窗口句柄。
        ("stale", 0)     —— 有互斥体但始终没有窗口（旧进程卡住了），照常启动新窗口。
        """
        global _MUTEX_HANDLE
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        _MUTEX_HANDLE = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        if ctypes.get_last_error() != ERROR_ALREADY_EXISTS:
            return "new", 0

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.FindWindowW.restype = ctypes.c_void_p
        user32.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
        deadline = time.time() + WAIT_EXISTING_WINDOW_S
        while time.time() < deadline:
            # 字幕模式下主窗口隐藏，优先激活真正可见的字幕条，避免二次启动把主控制台弹出。
            hwnd = user32.FindWindowW(None, "悬浮字幕")
            if not hwnd:
                hwnd = user32.FindWindowW(None, APP_NAME)
            if hwnd:
                return "existing", int(hwnd)
            time.sleep(0.1)
        return "stale", 0


    def _bring_to_front(hwnd: int) -> None:
        """把已有窗口拉到前台并强制重绘一次（透明无边框窗口偶尔会停在空白画面）。"""
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.ShowWindow(ctypes.c_void_p(hwnd), SW_RESTORE)
            user32.SetForegroundWindow(ctypes.c_void_p(hwnd))
            user32.RedrawWindow(ctypes.c_void_p(hwnd), None, None,
                                RDW_INVALIDATE | RDW_ALLCHILDREN | RDW_UPDATENOW)
        except Exception:  # noqa: BLE001
            pass


    def _refresh_window(win) -> None:
        """逼窗口把画面真正画到屏幕上：个别显卡/主题下首帧会停在空白。"""
        try:
            win.update()
            win.repaint()
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.RedrawWindow(ctypes.c_void_p(int(win.winId())), None, None,
                                RDW_INVALIDATE | RDW_UPDATENOW)
        except Exception:  # noqa: BLE001
            pass


    def _excepthook(exc_type, exc, tb) -> None:
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} 未处理异常 =====\n{text}")
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc, tb)


    def _report_fatal(exc_type, exc, tb) -> None:
        """启动阶段的致命错误：写日志 + 弹窗，避免双击后窗口一闪就没。"""
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} 启动失败 =====\n{text}")
        except Exception:
            pass
        try:
            app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
            QtWidgets.QMessageBox.critical(
                None,
                f"{APP_NAME} 启动失败",
                "程序遇到错误，无法继续运行：\n\n"
                f"{exc_type.__name__}: {exc}\n\n"
                f"完整错误信息已保存到：\n{LOG_PATH}",
            )
        except Exception:
            pass


    def _run() -> int:
        try:
            return main()
        except SystemExit:
            raise
        except BaseException:  # noqa: BLE001 - 兜底，保证错误可见
            _report_fatal(*sys.exc_info())
            return 1


    def _selftest(cfg: Config) -> int:
        from .core.asr import FinalASR
        from .paths import MODELS

        checks = [
            ("日语高速识别 Parakeet", FinalASR.available("parakeet")),
            ("silero_vad.onnx", (MODELS / "silero_vad.onnx").exists()),
        ]
        for name, ok in checks:
            print(f"{'OK ' if ok else '-- '}  {name}")
        failed = not (FinalASR.available("parakeet") and (MODELS / "silero_vad.onnx").is_file())
        return 1 if failed else 0


    def main(argv: list[str] | None = None) -> int:
        ap = argparse.ArgumentParser(prog="jpsub", description=f"{APP_NAME} v{__version__}")
        ap.add_argument("--config", type=str, default=None, help="指定配置文件路径")
        ap.add_argument("--screenshot", type=str, default=None, help="渲染主界面截图到指定路径后退出（用于自检）")
        ap.add_argument("--drawer", action="store_true", help="截图时展开设置面板")
        ap.add_argument("--drawer-scroll", type=int, default=0, help="截图前把设置面板滚动到指定像素")
        ap.add_argument("--overlay-shot", type=str, default=None, help="渲染悬浮字幕窗截图到指定路径后退出")
        ap.add_argument("--selftest", action="store_true", help="检查模型是否齐全")
        ap.add_argument("--main-window", action="store_true",
                        help="使用传统主窗口模式（默认仅显示悬浮字幕条）")
        args = ap.parse_args(argv)

        ensure_dirs()
        sys.excepthook = _excepthook
        cfg = Config(Path(args.config) if args.config else CONFIG_PATH)

        if args.selftest:
            return _selftest(cfg)

        if args.screenshot is None and args.overlay_shot is None:
            state, hwnd = _existing_window()
            if state == "existing":
                _bring_to_front(hwnd)
                _log("已有实例在运行，已把它的窗口带到前台")
                print("程序已在运行，已把窗口带到前台。")
                return 0
            if state == "stale":
                _log("上一次的进程没有留下窗口（可能已卡死），按新启动处理")

        app = QtWidgets.QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(__version__)
        icon_path = ASSETS / "icon.png"
        if icon_path.exists():
            app.setWindowIcon(QtGui.QIcon(str(icon_path)))

        _log(f"开始构建主窗口（v{__version__}）")
        from .ui.window import MainWindow

        win = MainWindow(cfg)
        overlay_only = (not args.main_window and args.screenshot is None
                        and args.overlay_shot is None)
        if overlay_only:
            # 强制为隐藏的控制器创建原生窗口句柄：单实例检测的 FindWindowW 才能
            # 在工具栏暂时不可见时正确发现当前进程，不会错误地启动第二份模型。
            win.winId()
            # MainWindow 依然负责音频、识别、翻译和字幕数据，但不作为第二个可见窗口。
            app.setQuitOnLastWindowClosed(False)
            win.enter_overlay_mode(start_listening=not bool(cfg.load_error))
            _log(f"字幕条单窗口模式已启动（{time.perf_counter() - _T_START:.2f}s）")
        else:
            win.show()
            _log(f"主窗口已显示（进程启动后 {time.perf_counter() - _T_START:.2f} 秒）")
        if cfg.load_error and args.screenshot is None and args.overlay_shot is None:
            _log(f"配置文件读取失败；已保留原件并暂停自动监听：{cfg.path}")
            QtCore.QTimer.singleShot(0, win.notify_config_failure)
            # 首帧兜底：窗口显示后再强制重绘几次
            for delay_ms in (0, 250, 1200):
                QtCore.QTimer.singleShot(delay_ms, lambda: _refresh_window(win))

        if args.overlay_shot:
            def _shot_overlay() -> None:
                try:
                    ov = win._ensure_overlay()
                    ov.set_content([
                        ("ちょっと待って、今から新しいゲームやるよ！", "等一下，我现在要开始玩新游戏了！"),
                        ("このキャラ、マジで可愛くない？", "这个角色，是不是超级可爱？"),
                    ], live_index=1)
                    ov.setVisible(True)

                    def _grab() -> None:
                        ov.grab().save(args.overlay_shot)
                        print(f"截图已保存: {args.overlay_shot}")
                        app.quit()

                    QtCore.QTimer.singleShot(600, _grab)
                except Exception as e:  # noqa: BLE001
                    print(f"截图失败: {e}")
                    app.quit()

            QtCore.QTimer.singleShot(900, _shot_overlay)
            return app.exec()

        if args.screenshot:
            if args.drawer:
                win.btn_settings.setChecked(True)
            if args.drawer_scroll:
                QtCore.QTimer.singleShot(
                    400, lambda: win.settings.verticalScrollBar().setValue(int(args.drawer_scroll)))

            def _shot() -> None:
                try:
                    target = (win._settings_dialog
                              if args.drawer and win._settings_dialog is not None else win)
                    pm = target.grab()
                    pm.save(args.screenshot)
                    print(f"截图已保存: {args.screenshot}")
                except Exception as e:  # noqa: BLE001
                    print(f"截图失败: {e}")
                app.quit()

            QtCore.QTimer.singleShot(1200, _shot)

        return app.exec()


    if __name__ == "__main__":
        sys.exit(_run())
# END MODULE: jpsub.main

# ======================================================================
# BEGIN MODULE: jpsub.paths  (jpsub/paths.py)
# ======================================================================
if False:  # 可阅读的源码区块（独立模块由上方加载器执行）
    # -*- coding: utf-8 -*-
    import os
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]
    MODELS = Path(os.environ.get("JPSUB_MODEL_DIR", str(ROOT / "models")))
    ASSETS = Path(__file__).resolve().parent / "assets"
    BACKGROUNDS = ASSETS / "backgrounds"
    CACHE = ROOT / "work" / "cache"
    HISTORY = ROOT / "history"
    CONFIG_PATH = ROOT / "config.json"
    LOG_PATH = ROOT / "jpsub.log"


    def ensure_dirs() -> None:
        for d in (MODELS, BACKGROUNDS, CACHE, HISTORY):
            d.mkdir(parents=True, exist_ok=True)
# END MODULE: jpsub.paths

# ======================================================================
# BEGIN MODULE: jpsub.ui  (jpsub/ui/__init__.py)
# ======================================================================
if False:  # 可阅读的源码区块（独立模块由上方加载器执行）
    # -*- coding: utf-8 -*-
    pass  # __DISPLAY_ONLY__
# END MODULE: jpsub.ui

# ======================================================================
# BEGIN MODULE: jpsub.ui.background  (jpsub/ui/background.py)
# ======================================================================
if False:  # 可阅读的源码区块（独立模块由上方加载器执行）
    # -*- coding: utf-8 -*-
    """照片背景层：模糊、压暗、渐变，切换时淡入。"""
    # __FUTURE_IMPORT__ from __future__ import annotations

    import hashlib
    import json
    from pathlib import Path

    from PySide6 import QtCore, QtGui, QtWidgets

    from ..paths import BACKGROUNDS, CACHE


    def background_files() -> list[Path]:
        if not BACKGROUNDS.exists():
            return []
        exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        return sorted([p for p in BACKGROUNDS.iterdir() if p.suffix.lower() in exts])


    def load_credits() -> dict:
        f = BACKGROUNDS / "credits.json"
        if f.exists():
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}


    def resolve_background(name: str) -> Path | None:
        files = background_files()
        if not files:
            return None
        if not name or name == "auto":
            return files[0]
        for f in files:
            if f.name == name or f.stem == name:
                return f
        return files[0]


    class BackgroundLayer(QtWidgets.QWidget):
        """铺满窗口的照片背景；模糊/压暗/不透明度可调，切换时淡入。"""

        def __init__(self, parent=None):
            super().__init__(parent)
            self._cur: QtGui.QPixmap | None = None
            self._prev: QtGui.QPixmap | None = None
            self._scaled: dict[tuple, QtGui.QPixmap] = {}   # 按尺寸缓存的缩放结果
            self._fade = 1.0
            self._dim = 45
            self._opacity = 100
            self._name = ""
            self._blur = 16
            self._anim = QtCore.QVariantAnimation(self)
            self._anim.setDuration(450)
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
            self._anim.valueChanged.connect(self._on_fade)
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        def _on_fade(self, v) -> None:
            self._fade = float(v)
            self.update()

        def _scaled_for(self, pm: QtGui.QPixmap, size: QtCore.QSize) -> QtGui.QPixmap:
            """把背景图缩放到窗口大小（带缓存）。

            以前每次重绘都要平滑缩放一张上千像素的图；淡入动画 450 毫秒里要重绘几十次，
            白白占着 UI 线程。缓存之后同一张图同一尺寸只算一次。
            """
            key = (size.width(), size.height(), pm.cacheKey())
            hit = self._scaled.get(key)
            if hit is not None:
                return hit
            out = pm.scaled(size, QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                            QtCore.Qt.TransformationMode.SmoothTransformation)
            if len(self._scaled) > 3:
                self._scaled.clear()
            self._scaled[key] = out
            return out

        def _blurred_pixmap(self, path: Path, size: QtCore.QSize, blur: int) -> QtGui.QPixmap | None:
            if size.width() <= 0 or size.height() <= 0:
                return None
            # 同名图片被替换后不能继续使用上一版本的模糊缓存。
            # 用完整路径及文件元数据作缓存键，比每次解码前计算整图哈希更轻量。
            try:
                source_stat = path.stat()
            except OSError:
                return None
            key = (f"{path.resolve()}_{source_stat.st_size}_{source_stat.st_mtime_ns}_"
                   f"{size.width()}x{size.height()}_{blur}")
            cache_file = CACHE / (hashlib.md5(key.encode()).hexdigest() + ".jpg")
            if not cache_file.exists():
                try:
                    from PIL import Image, ImageFilter

                    img = Image.open(path).convert("RGB")
                    sw, sh = img.size
                    scale = max(size.width() / sw, size.height() / sh)
                    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
                    img = img.resize((nw, nh), Image.LANCZOS)
                    left = (nw - size.width()) // 2
                    top = (nh - size.height()) // 2
                    img = img.crop((left, top, left + size.width(), top + size.height()))
                    if blur > 0:
                        radius = max(0.5, blur * size.height() / 900.0)
                        img = img.filter(ImageFilter.GaussianBlur(radius))
                    CACHE.mkdir(parents=True, exist_ok=True)
                    img.save(cache_file, quality=88)
                except Exception:
                    return QtGui.QPixmap(str(path))
            pm = QtGui.QPixmap(str(cache_file))
            return pm if not pm.isNull() else None

        def set_background(self, name: str, blur: int, dim: int, opacity: int = 100,
                           animate: bool = True) -> None:
            self._name, self._blur = name, blur
            self._dim = dim
            self._opacity = opacity
            size = self.size()
            if size.isEmpty():
                size = QtCore.QSize(1100, 700)
            path = resolve_background(name)
            pm = self._blurred_pixmap(path, size, blur) if path else None
            if pm is None:
                self._cur = None
                self.update()
                return
            if self._cur is not None and animate:
                self._prev = self._cur
                self._cur = pm
                self._anim.stop()
                self._anim.start()
            else:
                self._prev = None
                self._cur = pm
                self._fade = 1.0
                self.update()

        def set_tuning(self, dim: int, opacity: int) -> None:
            self._dim = dim
            self._opacity = opacity
            self.update()

        def reflow(self) -> None:
            """窗口尺寸变化后重新生成背景图（带缓存，代价很低）。"""
            if self._name:
                self.set_background(self._name, self._blur, self._dim, self._opacity, animate=False)

        def paintEvent(self, event) -> None:
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
            rect = self.rect()
            clip = QtGui.QPainterPath()
            clip.addRoundedRect(QtCore.QRectF(rect), 14, 14)
            p.setClipPath(clip)
            p.fillRect(rect, QtGui.QColor("#101218"))
            layers = [(self._prev, 1.0 - self._fade), (self._cur, self._fade if self._prev else 1.0)]
            for pm, alpha in layers:
                if pm is None or alpha <= 0.01:
                    continue
                scaled = self._scaled_for(pm, rect.size())
                x = (scaled.width() - rect.width()) // 2
                y = (scaled.height() - rect.height()) // 2
                p.setOpacity(alpha * (self._opacity / 100.0))
                p.drawPixmap(-x, -y, scaled)
            p.setOpacity(self._opacity / 100.0)
            dim_a = max(0, min(230, int(self._dim * 2.3)))
            p.fillRect(rect, QtGui.QColor(8, 10, 16, dim_a))
            grad = QtGui.QLinearGradient(0, rect.height() * 0.35, 0, rect.height())
            grad.setColorAt(0.0, QtGui.QColor(8, 10, 16, 0))
            grad.setColorAt(1.0, QtGui.QColor(8, 10, 16, min(185, dim_a + 95)))
            p.fillRect(rect, QtGui.QBrush(grad))
# END MODULE: jpsub.ui.background

# ======================================================================
# BEGIN MODULE: jpsub.ui.overlay  (jpsub/ui/overlay.py)
# ======================================================================
if False:  # 可阅读的源码区块（独立模块由上方加载器执行）
    # -*- coding: utf-8 -*-
    """悬浮字幕条：置顶显示最近几句，可拖动/滚轮缩放字体/鼠标穿透。"""
    # __FUTURE_IMPORT__ from __future__ import annotations

    from PySide6 import QtCore, QtGui, QtWidgets


    class _Row(QtWidgets.QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self._jp_style = ""
            self._zh_style = ""
            lay = QtWidgets.QVBoxLayout(self)
            lay.setContentsMargins(12, 3, 12, 3)
            lay.setSpacing(1)
            self.jp = QtWidgets.QLabel("")
            self.zh = QtWidgets.QLabel("")
            self.jp.setWordWrap(True)
            self.zh.setWordWrap(True)
            self.jp.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.zh.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(self.jp)
            lay.addWidget(self.zh)

        def set_text(self, jp: str, zh: str, jp_size: int, zh_size: int, live: bool = False,
                     show_jp: bool = True, jp_bright: bool = False,
                     previous: bool = False, cfg=None) -> None:
            """参照 live-caption：旧句小字灰色，当前原文居中加粗，译文居中浅灰。"""
            _ = jp_bright, live
            color = lambda key, default: str(cfg.get(key, default)) if cfg else default
            show_jp = bool(show_jp)
            self.jp.setVisible(bool(jp) and show_jp)
            self.zh.setVisible(bool(zh) and (not previous or not show_jp))
            if self.jp.text() != jp:
                self.jp.setText(jp)
            if self.zh.text() != zh:
                self.zh.setText(zh)
            family = color("overlay.font_name", "Microsoft YaHei")
            f = self.zh.font()
            f.setFamily(family)
            f.setPointSize(max(10, round(zh_size * (0.7 if previous else 1))))
            f.setBold(False)
            if f != self.zh.font():
                self.zh.setFont(f)
            f2 = self.jp.font()
            f2.setFamily(family)
            f2.setPointSize(max(10, round(jp_size * (0.68 if previous else 1))))
            f2.setBold(not previous and bool(cfg.get("overlay.current_bold", True) if cfg else True))
            if f2 != self.jp.font():
                self.jp.setFont(f2)
            jp_color = color("overlay.previous_color", "#9a9a9a") if previous else color("overlay.current_color", "#ffffff")
            jp_style = f"color: {jp_color};"
            if jp_style != self._jp_style:
                self._jp_style = jp_style
                self.jp.setStyleSheet(jp_style)
            zh_style = f"color: {color('overlay.translation_color', '#d0d0d0')};"
            if zh_style != self._zh_style:
                self._zh_style = zh_style
                self.zh.setStyleSheet(zh_style)


    class OverlayWindow(QtWidgets.QWidget):
        """无边框置顶字幕窗。"""

        interaction_changed = QtCore.Signal()
        settings_requested = QtCore.Signal()
        listen_requested = QtCore.Signal()
        console_requested = QtCore.Signal()
        close_requested = QtCore.Signal()

        def __init__(self, cfg, parent=None):
            super().__init__(parent, QtCore.Qt.WindowType.FramelessWindowHint
                             | QtCore.Qt.WindowType.Tool
                             | QtCore.Qt.WindowType.WindowStaysOnTopHint)
            self.cfg = cfg
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setWindowTitle("悬浮字幕")
            self._rows: list[_Row] = []
            self._drag_pos: QtCore.QPoint | None = None
            self._bg_alpha = 212
            self._last_items: list[tuple[str, str]] = []
            self._last_live: int | None = None

            outer = QtWidgets.QVBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)
            self.panel = QtWidgets.QWidget(self)
            self.panel.installEventFilter(self)
            outer.addWidget(self.panel)
            self.vbox = QtWidgets.QVBoxLayout(self.panel)
            self.vbox.setContentsMargins(2, 6, 2, 6)
            self.vbox.setSpacing(2)
            # 上下各一根弹簧：字幕行按自身高度居中，灰框才不会比文字大一大圈
            self.vbox.addStretch(1)
            self.vbox.addStretch(1)

            self.tools = QtWidgets.QWidget(self)
            tl = QtWidgets.QHBoxLayout(self.tools)
            tl.setContentsMargins(0, 0, 6, 0)
            tl.setSpacing(4)
            self.btn_settings = QtWidgets.QPushButton("⚙ 设置")
            self.btn_listen = QtWidgets.QPushButton("▶ 开始")
            self.btn_console = QtWidgets.QPushButton("显示主界面")
            self.btn_lock = QtWidgets.QPushButton("锁定位置")
            self.btn_thru = QtWidgets.QPushButton("鼠标穿透")
            self.btn_close = QtWidgets.QPushButton("×")
            for b in (self.btn_settings, self.btn_listen, self.btn_console,
                      self.btn_lock, self.btn_thru, self.btn_close):
                b.setObjectName("ghost")
                b.setFixedHeight(22)
                b.setStyleSheet("font-size: 11px; padding: 1px 8px;")
            self.btn_lock.setCheckable(True)
            self.btn_thru.setCheckable(True)
            tl.addStretch(1)
            tl.addWidget(self.btn_settings)
            tl.addWidget(self.btn_listen)
            tl.addWidget(self.btn_console)
            tl.addWidget(self.btn_lock)
            tl.addWidget(self.btn_thru)
            tl.addWidget(self.btn_close)
            self.tools.hide()
            self.btn_settings.clicked.connect(self.settings_requested.emit)
            self.btn_listen.clicked.connect(self.listen_requested.emit)
            self.btn_console.clicked.connect(self.console_requested.emit)
            self.btn_lock.clicked.connect(self._toggle_lock)
            self.btn_thru.clicked.connect(self._toggle_through)
            self.btn_close.clicked.connect(self.close_requested.emit)

            self._apply_alpha()
            self._apply_flags()
            self._restore_geometry()
            self._sync_rows()

        # ------------------------------------------------------------------
        def _apply_alpha(self) -> None:
            self._bg_alpha = int(self.cfg.get("overlay.opacity", 85) / 100 * 255)
            self._apply_text_effects()
            self.update()

        def _apply_text_effects(self) -> None:
            """背景越透明，越要给文字加黑色描边（阴影），否则叠在直播画面上看不清。"""
            want = bool(self.cfg.get("overlay.text_shadow", True))
            dark = 1.0 - min(1.0, self._bg_alpha / 190.0)
            for row in self._rows:
                for lbl in (row.jp, row.zh):
                    eff = lbl.graphicsEffect()
                    if want and dark > 0.05:
                        if not isinstance(eff, QtWidgets.QGraphicsDropShadowEffect):
                            eff = QtWidgets.QGraphicsDropShadowEffect(lbl)
                            lbl.setGraphicsEffect(eff)
                        eff.setColor(QtGui.QColor(0, 0, 0, int(110 + 145 * dark)))
                        eff.setBlurRadius(2 + 4 * dark)
                        eff.setOffset(0, 0)
                    elif eff is not None:
                        lbl.setGraphicsEffect(None)

        def _apply_flags(self) -> None:
            locked = bool(self.cfg.get("overlay.locked", False))
            through = bool(self.cfg.get("overlay.click_through", False))
            if locked or through:
                self._drag_pos = None
            if bool(self.windowFlags() & QtCore.Qt.WindowType.WindowTransparentForInput) != through:
                visible = self.isVisible()
                self.setWindowFlag(QtCore.Qt.WindowType.WindowTransparentForInput, through)
                if visible:
                    self.show()
            self.btn_lock.setChecked(locked)
            self.btn_lock.setText("解除锁定" if locked else "锁定位置")
            self.btn_thru.setChecked(through)

        def _restore_geometry(self) -> None:
            w = int(self.cfg.get("overlay.w", 940))
            h = int(self.cfg.get("overlay.h", 150))
            x = self.cfg.get("overlay.x")
            y = self.cfg.get("overlay.y")
            self.resize(w, h)
            if x is None or y is None:
                screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
                x = screen.x() + (screen.width() - w) // 2
                y = screen.y() + screen.height() - h - 90
            self.move(int(x), int(y))

        def _save_geometry(self) -> None:
            if self.cfg.load_error:
                return  # Never replace damaged user config on overlay movement.
            self.cfg.update_many({
                "overlay.x": self.x(), "overlay.y": self.y(),
                "overlay.w": self.width(), "overlay.h": self.height(),
            })

        # ------------------------------------------------------------------
        def _sync_rows(self) -> None:
            want = max(1, min(4, int(self.cfg.get("overlay.lines", 2))))
            if not bool(self.cfg.get("overlay.show_previous", True)):
                want = 1
            while len(self._rows) < want:
                row = _Row(self.panel)
                for widget in (row, row.jp, row.zh):
                    widget.installEventFilter(self)
                self._rows.append(row)
                # 插在底部弹簧之前，保证上下留白对称
                self.vbox.insertWidget(self.vbox.count() - 1, row)
            while len(self._rows) > want:
                row = self._rows.pop()
                self.vbox.removeWidget(row)
                row.deleteLater()
            self._apply_text_effects()

        def set_content(self, items: list[tuple[str, str]], live_index: int | None = None,
                        force: bool = False) -> None:
            """items: [(jp, zh), ...] 从旧到新；live_index 指向实时行的下标。

            内容没变就直接返回：主窗口每次草稿刷新都会调这里，没必要把控件全重设一遍。
            """
            if not force and items == self._last_items and live_index == self._last_live:
                return
            self._sync_rows()
            self._last_items, self._last_live = items, live_index
            n = len(self._rows)
            shown = items[-n:]
            pad = n - len(shown)
            jp_size = int(self.cfg.get("overlay.jp_size", 15))
            zh_size = int(self.cfg.get("overlay.zh_size", 24))
            base = len(items) - len(shown)
            # 悬浮字幕里的日语原文由自己这一项控制（主窗口的「显示模式」互不影响）
            show_jp = bool(self.cfg.get("overlay.show_jp", True))
            jp_bright = self._bg_alpha < 120          # 背景很透明时，日文原文也调亮一点
            for i, row in enumerate(self._rows):
                k = i - pad
                if 0 <= k < len(shown):
                    jp, zh = shown[k]
                    row.set_text(jp, zh, jp_size, zh_size,
                                 live=(live_index is not None and base + k == live_index),
                                 show_jp=show_jp, jp_bright=jp_bright,
                                 previous=(i != n - 1), cfg=self.cfg)
                else:
                    row.set_text("", "", jp_size, zh_size, show_jp=show_jp,
                                 jp_bright=jp_bright, previous=(i != n - 1), cfg=self.cfg)
            self._place_tools()

        def refresh(self) -> None:
            self._apply_flags()
            self._apply_alpha()
            self.set_content(self._last_items, self._last_live, force=True)

        def _place_tools(self) -> None:
            tool_width = min(485, self.width())
            self.tools.setGeometry(max(0, self.width() - tool_width - 4), 4, tool_width, 24)
            self.tools.raise_()

        # ------------------------------------------------------------------
        def _bg_rect(self) -> QtCore.QRect:
            """灰框只包住文字本身：字少框就小，不会留一大片灰底。"""
            rect = QtCore.QRect()
            for row in self._rows:
                if not row.isVisible():
                    continue
                base = row.mapTo(self, QtCore.QPoint(0, 0))
                for lbl in (row.jp, row.zh):
                    if not lbl.isVisible() or not lbl.text():
                        continue
                    ink = QtGui.QFontMetrics(lbl.font()).horizontalAdvance(lbl.text())
                    w = max(1, min(lbl.width(), ink))
                    r = QtCore.QRect(base + QtCore.QPoint(lbl.x(), lbl.y()),
                                     QtCore.QSize(w, lbl.height()))
                    rect = r if rect.isNull() else rect.united(r)
            if rect.isNull():
                return self.rect().adjusted(1, 1, -1, -1)
            pad_x, pad_y = 10, 5
            return rect.adjusted(-pad_x, -pad_y, pad_x, pad_y).intersected(
                self.rect().adjusted(1, 1, -1, -1))

        def paintEvent(self, event) -> None:
            """Local live-caption 同款：纯黑透明背景整条铺满，不画圆角卡片。"""
            if self._bg_alpha <= 0:
                return
            painter = QtGui.QPainter(self)
            color = QtGui.QColor(str(self.cfg.get("overlay.background_color", "#000000")))
            if not color.isValid():
                color = QtGui.QColor("#000000")
            color.setAlpha(self._bg_alpha)
            painter.fillRect(self.rect(), color)

        def enterEvent(self, e) -> None:
            if not self.cfg.get("overlay.click_through", False):
                self.tools.show()
            super().enterEvent(e)

        def leaveEvent(self, e) -> None:
            self.tools.hide()
            super().leaveEvent(e)

        # ------------------------------------------------------------------
        def _toggle_lock(self) -> None:
            locked = not bool(self.cfg.get("overlay.locked", False))
            self.cfg.set("overlay.locked", locked)
            self._apply_flags()
            self.interaction_changed.emit()

        def _toggle_through(self) -> None:
            through = not bool(self.cfg.get("overlay.click_through", False))
            self.cfg.set("overlay.click_through", through)
            self._apply_flags()
            self.interaction_changed.emit()

        def eventFilter(self, obj, event) -> bool:
            if obj is self.panel or obj in self._rows or any(
                    obj is label for row in self._rows for label in (row.jp, row.zh)):
                if self._handle_drag_event(event):
                    return True
            return bool(super().eventFilter(obj, event))

        def _handle_drag_event(self, e) -> bool:
            kind = e.type()
            if (kind == QtCore.QEvent.Type.MouseButtonPress
                    and e.button() == QtCore.Qt.MouseButton.LeftButton
                    and not self.cfg.get("overlay.locked", False)
                    and not self.cfg.get("overlay.click_through", False)):
                self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            elif kind == QtCore.QEvent.Type.MouseMove and self._drag_pos is not None:
                self.move(e.globalPosition().toPoint() - self._drag_pos)
            elif kind == QtCore.QEvent.Type.MouseButtonRelease and self._drag_pos is not None:
                self._drag_pos = None
                self._save_geometry()
            else:
                return False
            e.accept()
            return True

        # 拖动与滚轮 ---------------------------------------------------------
        def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
            if not self._handle_drag_event(e):
                super().mousePressEvent(e)

        def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
            if not self._handle_drag_event(e):
                super().mouseMoveEvent(e)

        def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
            if not self._handle_drag_event(e):
                super().mouseReleaseEvent(e)

        def mouseDoubleClickEvent(self, e) -> None:
            self._toggle_through()

        def wheelEvent(self, e) -> None:
            delta = 1 if e.angleDelta().y() > 0 else -1
            zh = max(14, min(60, int(self.cfg.get("overlay.zh_size", 24)) + delta))
            self.cfg.update_many({"overlay.zh_size": zh, "overlay.jp_size": max(10, zh - 9)})
            self.refresh()
            e.accept()

        def resizeEvent(self, e) -> None:
            self._place_tools()
            self._save_geometry()
            super().resizeEvent(e)
# END MODULE: jpsub.ui.overlay

# ======================================================================
# BEGIN MODULE: jpsub.ui.settings  (jpsub/ui/settings.py)
# ======================================================================
if False:  # 可阅读的源码区块（独立模块由上方加载器执行）
    # -*- coding: utf-8 -*-
    """设置抽屉：音频、识别、翻译、界面外观、悬浮字幕、关于。"""
    # __FUTURE_IMPORT__ from __future__ import annotations

    import threading
    import shutil
    import re
    import subprocess
    import tempfile
    from pathlib import Path

    from PySide6 import QtCore, QtGui, QtWidgets

    from ..core import audio as audio_mod
    from ..core.asr import FinalASR
    from ..core.config import TRANSLATE_PRESETS
    from ..core.translate import Translator
    from ..paths import BACKGROUNDS, MODELS
    from . import theme as theme_mod
    from .background import background_files, load_credits, resolve_background


    def _hline() -> QtWidgets.QFrame:
        f = QtWidgets.QFrame()
        f.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        f.setStyleSheet("color: rgba(255,255,255,0.06);")
        f.setFixedHeight(1)
        return f


    def breakable(text: str) -> str:
        """在长路径/文件名里插入零宽空格，让它们能换行——否则会把设置面板撑宽、右边被裁掉。"""
        out: list[str] = []
        for ch in str(text):
            out.append(ch)
            if ch in "/\\_-.":
                out.append("\u200b")
        return "".join(out)


    class SettingsPanel(QtWidgets.QScrollArea):
        """右侧设置面板；任何改动都会写回 config 并发出 changed 信号。"""

        changed = QtCore.Signal(str, object)
        speed_llama = QtCore.Signal(str)
        eng_progress = QtCore.Signal(str, int, int)
        eng_finished = QtCore.Signal(str)

        def __init__(self, cfg, parent=None):
            super().__init__(parent)
            self.cfg = cfg
            self._llama_job = None
            self.setWidgetResizable(True)
            self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
            self.setMinimumWidth(340)
            # 上限放宽：抽屉宽度由主窗口按内容实际需要的宽度决定（否则内容右边会被裁掉）
            self.setMaximumWidth(560)
            root = QtWidgets.QWidget()
            root.setStyleSheet("background: transparent;")
            self.vbox = QtWidgets.QVBoxLayout(root)
            self.vbox.setContentsMargins(12, 4, 12, 16)
            self.vbox.setSpacing(10)
            self.setWidget(root)
            self._build(self.vbox)
            self.vbox.addStretch(1)
            self._guard_wheel()

        # ------------------------------------------------------------- 工具
        def _make_progress(self, parent_lay) -> tuple[QtWidgets.QProgressBar, QtWidgets.QLabel]:
            bar = QtWidgets.QProgressBar()
            bar.setTextVisible(False)
            bar.setFixedHeight(6)
            bar.hide()
            lbl = QtWidgets.QLabel("")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("font-size: 11px; color: rgba(170,178,195,0.95);")
            lbl.hide()
            parent_lay.addWidget(bar)
            parent_lay.addWidget(lbl)
            return bar, lbl

        def _combo(self) -> QtWidgets.QComboBox:
            c = QtWidgets.QComboBox()
            c.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            c.setMinimumContentsLength(8)
            c.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
            return c

        def _section(self, title: str) -> QtWidgets.QVBoxLayout:
            card = QtWidgets.QFrame()
            card.setObjectName("card")
            lay = QtWidgets.QVBoxLayout(card)
            lay.setContentsMargins(12, 10, 12, 12)
            lay.setSpacing(8)
            lbl = QtWidgets.QLabel(title)
            lbl.setObjectName("sectionTitle")
            lay.addWidget(lbl)
            self.vbox.addWidget(card)
            return lay

        def _row(self, parent_lay, label: str, sub: str = "") -> QtWidgets.QHBoxLayout:
            holder = QtWidgets.QVBoxLayout()
            holder.setSpacing(2)
            line = QtWidgets.QHBoxLayout()
            name = QtWidgets.QLabel(label)
            name.setFixedWidth(84)
            name.setStyleSheet("color: rgba(205,212,225,0.9);")
            line.addWidget(name)
            line.addStretch(0)
            holder.addLayout(line)
            if sub:
                tip = QtWidgets.QLabel(sub)
                tip.setObjectName("faint")
                tip.setWordWrap(True)
                tip.setStyleSheet("font-size: 11px; color: rgba(150,158,175,0.9);")
                holder.addWidget(tip)
            parent_lay.addLayout(holder)
            return line

        def _set(self, path: str, value, signal: str) -> None:
            self.cfg.set(path, value)
            self.changed.emit(path, value)

        def _bind_combo(self, combo: QtWidgets.QComboBox, path: str) -> None:
            combo.currentIndexChanged.connect(
                lambda _i: self._set(path, combo.itemData(combo.currentIndex()), None))

        def _bind_check(self, box: QtWidgets.QCheckBox, path: str) -> None:
            box.toggled.connect(lambda v: self._set(path, bool(v), None))

        def _bind_slider(self, slider: QtWidgets.QSlider, path: str, mapper=None) -> None:
            def _on(v: int) -> None:
                val = mapper(v) if mapper else v
                self._set(path, val, None)
            slider.valueChanged.connect(_on)

        # ---- 防止「滚动时误改设置」 -------------------------------------------
        def _guard_wheel(self) -> None:
            """在设置面板里滚动时，鼠标划过下拉框/滑条不应把值改掉（要改得先点它）。"""
            for cls in (QtWidgets.QComboBox, QtWidgets.QSlider, QtWidgets.QSpinBox,
                        QtWidgets.QDoubleSpinBox):
                for w in self.findChildren(cls):
                    w.installEventFilter(self)

        def eventFilter(self, obj, ev) -> bool:
            if (ev.type() == QtCore.QEvent.Type.Wheel
                    and isinstance(obj, (QtWidgets.QComboBox, QtWidgets.QSlider,
                                         QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox))):
                # 即使刚点过控件、它仍有焦点，滚轮也只滚动设置页，不修改选项。
                delta = ev.pixelDelta().y() or ev.angleDelta().y()
                bar = self.verticalScrollBar()
                bar.setValue(bar.value() - int(delta))
                ev.accept()
                return True
            return bool(super().eventFilter(obj, ev))

        # ------------------------------------------------------------- 构建
        def _build(self, vbox: QtWidgets.QVBoxLayout) -> None:  # noqa: C901
            self._build_caption_appearance()
            self._build_audio()
            self._build_asr()
            self._build_translate()
            self._build_ui()
            self._build_overlay()
            self._build_about()

        # ---- live-caption 字幕条外观：设置窗口顶部快速调整 --------------------
        def _build_caption_appearance(self) -> None:
            lay = self._section("字幕窗口外观 · Live Caption")
            note = QtWidgets.QLabel(
                "底部无边框字幕条：当前日语居中加粗，译文在下方，上一句缩小变灰。"
                "颜色、字体、透明度即时生效；历史记录仍保存在主窗口。")
            note.setWordWrap(True)
            lay.addWidget(note)

            r = self._row(lay, "字体")
            fonts = sorted(set(QtGui.QFontDatabase.families())
                           | (set(theme_mod.FONT_PRESETS) - {"系统默认"}))
            font_box = self._combo()
            font_box.addItems(fonts)
            current = str(self.cfg.get("overlay.font_name", "Microsoft YaHei"))
            if font_box.findText(current) < 0:
                font_box.insertItem(0, current)
            font_box.setCurrentText(current)
            font_box.currentTextChanged.connect(lambda text: self._set("overlay.font_name", text, None))
            r.addWidget(font_box, 1)
            self.cmb_caption_font = font_box

            for label, key, lower, upper, default in (
                ("原文字号", "overlay.jp_size", 12, 80, 30),
                ("译文字号", "overlay.zh_size", 12, 80, 25),
                ("历史字幕数量", "overlay.history_count", 0, 3, 1),
                ("背景透明度", "overlay.opacity", 0, 100, 85),
            ):
                row = self._row(lay, label)
                slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
                slider.setRange(lower, upper)
                if key == "overlay.history_count":
                    value = max(0, int(self.cfg.get("overlay.lines", 2)) - 1)
                else:
                    value = int(self.cfg.get(key, default))
                slider.setValue(value)
                label_value = QtWidgets.QLabel(str(value) + ("%" if key == "overlay.opacity" else ""))
                label_value.setFixedWidth(55)
                def apply(v, path=key, display=label_value):
                    display.setText(str(v) + ("%" if path == "overlay.opacity" else ""))
                    if path == "overlay.history_count":
                        self._set("overlay.lines", int(v) + 1, None)
                    else:
                        self._set(path, int(v), None)
                slider.valueChanged.connect(apply)
                row.addWidget(slider, 1)
                row.addWidget(label_value)
            for label, path, default in (
                ("当前日语颜色", "overlay.current_color", "#ffffff"),
                ("中文翻译颜色", "overlay.translation_color", "#d0d0d0"),
                ("历史字幕颜色", "overlay.previous_color", "#9a9a9a"),
                ("背景颜色", "overlay.background_color", "#000000"),
            ):
                row = self._row(lay, label)
                button = QtWidgets.QPushButton("选择颜色")
                color = str(self.cfg.get(path, default))
                button.setStyleSheet(f"background: {color}; border: 1px solid #777; color: "
                                     + ("white" if QtGui.QColor(color).lightness() < 125 else "black") + ";")
                def choose(_checked=False, key=path, btn=button):
                    current_color = QtGui.QColor(str(self.cfg.get(key, default)))
                    selected = QtWidgets.QColorDialog.getColor(current_color, self, "选择字幕颜色")
                    if selected.isValid():
                        shade = selected.name()
                        self._set(key, shade, None)
                        ink = "white" if selected.lightness() < 125 else "black"
                        btn.setStyleSheet(
                            f"background: {shade}; border: 1px solid #777; color: {ink};")
                button.clicked.connect(choose)
                row.addWidget(button)
            checks = QtWidgets.QHBoxLayout()
            bold = QtWidgets.QCheckBox("当前字幕粗体")
            bold.setChecked(bool(self.cfg.get("overlay.current_bold", True)))
            self._bind_check(bold, "overlay.current_bold")
            checks.addWidget(bold)
            history = QtWidgets.QCheckBox("显示历史字幕")
            history.setChecked(bool(self.cfg.get("overlay.show_previous", True)))
            self._bind_check(history, "overlay.show_previous")
            checks.addWidget(history)
            checks.addStretch()
            lay.addLayout(checks)

        # ---- 音频 ---------------------------------------------------------
        def _build_audio(self) -> None:
            lay = self._section("音频来源")
            line = self._row(lay, "来源")
            self.cmb_source = self._combo()
            self.cmb_source.addItem("系统声音（直播）", "loopback")
            self.cmb_source.addItem("麦克风（说话）", "mic")
            cur = str(self.cfg.get("audio.source", "loopback"))
            self.cmb_source.setCurrentIndex(0 if cur == "loopback" else 1)
            self._bind_combo(self.cmb_source, "audio.source")
            line.addWidget(self.cmb_source)

            line2 = self._row(lay, "设备")
            self.cmb_device = self._combo()
            btn_ref = QtWidgets.QPushButton("↻")
            btn_ref.setObjectName("ghost")
            btn_ref.setFixedWidth(34)
            btn_ref.clicked.connect(self._refresh_devices)
            line2.addWidget(self.cmb_device, 1)
            line2.addWidget(btn_ref)
            self._refresh_devices()
            sub = QtWidgets.QLabel("系统声音默认捕获「扬声器/耳机」里正在播放的内容；若你戴蓝牙耳机，请先播放再点刷新。")
            sub.setWordWrap(True)
            sub.setStyleSheet("font-size: 11px; color: rgba(150,158,175,0.9);")
            lay.addWidget(sub)

            line3 = self._row(lay, "断句速度", f"当前：{self.cfg.get('vad.min_silence_ms', 350)} 毫秒静音后断句")
            self.sld_silence = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            self.sld_silence.setRange(150, 900)
            self.sld_silence.setValue(int(self.cfg.get("vad.min_silence_ms", 350)))
            self._lbl_silence = QtWidgets.QLabel(f"{self.sld_silence.value()} ms")
            self._lbl_silence.setFixedWidth(58)
            self._lbl_silence.setStyleSheet("color: rgba(200,208,220,0.85);")

            def _sil(v: int) -> None:
                self._lbl_silence.setText(f"{v} ms")
                self._set("vad.min_silence_ms", int(v), None)
            self.sld_silence.valueChanged.connect(_sil)
            line3.addWidget(self.sld_silence, 1)
            line3.addWidget(self._lbl_silence)

            line4 = self._row(lay, "人声灵敏度")
            self.sld_thresh = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            self.sld_thresh.setRange(30, 80)
            self.sld_thresh.setValue(int(float(self.cfg.get("vad.threshold", 0.5)) * 100))
            self._bind_slider(self.sld_thresh, "vad.threshold", lambda v: round(v / 100.0, 2))
            self._lbl_thresh = QtWidgets.QLabel(f"{self.sld_thresh.value() / 100:.2f}")
            self._lbl_thresh.setFixedWidth(45)
            self.sld_thresh.valueChanged.connect(
                lambda v: self._lbl_thresh.setText(f"{v / 100:.2f}"))
            line4.addWidget(self.sld_thresh, 1)
            line4.addWidget(self._lbl_thresh)

        def _refresh_devices(self) -> None:
            self.cmb_device.blockSignals(True)
            self.cmb_device.clear()
            self.cmb_device.addItem("默认设备（推荐）", "")
            devs = audio_mod.list_devices()
            src = self.cmb_source.currentData() if hasattr(self, "cmb_source") else "loopback"
            for name in devs.get("mic" if src == "mic" else "loopback", []):
                self.cmb_device.addItem(name, name)
            cur = str(self.cfg.get("audio.device", "") or "")
            idx = self.cmb_device.findData(cur)
            self.cmb_device.setCurrentIndex(idx if idx >= 0 else 0)
            self.cmb_device.blockSignals(False)
            if not getattr(self, "_device_signal_bound", False):
                self.cmb_device.currentIndexChanged.connect(
                    lambda _i: self._set("audio.device", self.cmb_device.currentData(), None))
                self._device_signal_bound = True

        # ---- 识别 ---------------------------------------------------------
        def _build_asr(self) -> None:
            lay = self._section("语音识别")
            self.cfg.update_many({"asr.final_engine": "parakeet"}, save=False)
            self.cfg.save()

            ready = FinalASR.available("parakeet")
            status = QtWidgets.QLabel(
                ("✅ 日语高速识别已就绪" if ready else "❌ 日语识别模型缺失")
                + "\n日语专用 Parakeet：使用 CPU 识别人声，把显卡留给翻译。无需选择识别模型。"
            )
            status.setWordWrap(True)
            status.setStyleSheet(
                "font-size: 12px; color: " + ("#9fdcae;" if ready else "#ffb3b3;")
            )
            lay.addWidget(status)

            line0 = self._row(lay, "实时字幕", "约每 0.5 秒更新识别；译文边生成边显示，关闭可降低 CPU 占用")
            self.cmb_draft = self._combo()
            self.cmb_draft.addItem("开启（推荐）", "rolling")
            self.cmb_draft.addItem("关闭", "off")
            cur_draft = str(self.cfg.get("asr.draft_mode", "rolling"))
            if not bool(self.cfg.get("asr.partial", True)) or cur_draft == "off":
                cur_draft = "off"
            else:
                cur_draft = "rolling"
            i = self.cmb_draft.findData(cur_draft)
            self.cmb_draft.setCurrentIndex(max(0, i))
            self._bind_combo(self.cmb_draft, "asr.draft_mode")
            line0.addWidget(self.cmb_draft, 1)

            line2 = self._row(lay, "最长句长", "超长会自动切断，避免翻译跟不上")
            self.spn_max = QtWidgets.QSpinBox()
            self.spn_max.setRange(8, 30)
            self.spn_max.setSuffix(" 秒")
            self.spn_max.setValue(int(self.cfg.get("asr.max_segment_s", 24)))
            self.spn_max.valueChanged.connect(lambda v: self._set("asr.max_segment_s", int(v), None))
            line2.addWidget(self.spn_max)

        # ---- 翻译 ---------------------------------------------------------
        def _build_translate(self) -> None:
            lay = self._section("翻译服务")
            box = QtWidgets.QCheckBox("启用翻译")
            box.setChecked(bool(self.cfg.get("translate.enabled", True)))
            self._bind_check(box, "translate.enabled")
            lay.addWidget(box)
            tip = QtWidgets.QLabel("默认使用混元 Hy-MT2 7B，也可以选择微软或谷歌免密钥在线翻译。")
            tip.setWordWrap(True)
            tip.setStyleSheet("font-size: 11px; color: rgba(150,158,175,0.95);")
            lay.addWidget(tip)

            line = self._row(lay, "服务")
            self.cmb_provider = self._combo()
            for key, info in TRANSLATE_PRESETS.items():
                self.cmb_provider.addItem(info["label"], key)
            cur = str(self.cfg.get("translate.provider", "llamacpp"))
            self.cmb_provider.setCurrentIndex(max(0, self.cmb_provider.findData(cur)))
            self.cmb_provider.currentIndexChanged.connect(self._on_provider_changed)
            line.addWidget(self.cmb_provider, 1)

            self.lbl_hint = QtWidgets.QLabel("")
            self.lbl_hint.setWordWrap(True)
            self.lbl_hint.setStyleSheet("font-size: 11px; color: rgba(150,158,175,0.95);")
            lay.addWidget(self.lbl_hint)

            # ---- 内置引擎（llama.cpp）面板
            self.llama_box = QtWidgets.QFrame()
            el = QtWidgets.QVBoxLayout(self.llama_box)
            el.setContentsMargins(0, 2, 0, 0)
            el.setSpacing(6)
            self.lbl_llama_status = QtWidgets.QLabel("正在检查内置引擎…")
            self.lbl_llama_status.setWordWrap(True)
            self.lbl_llama_status.setStyleSheet("font-size: 11px; color: rgba(180,188,205,0.95);")
            el.addWidget(self.lbl_llama_status)
            engine_grid = QtWidgets.QGridLayout()
            engine_grid.setHorizontalSpacing(12)
            self.engine_status_labels = {}
            self.engine_download_buttons = {}
            for row, (variant, title) in enumerate((
                ('cpu', '通用引擎（CPU）'),
                ('vulkan', '显卡加速（Vulkan）'),
                ('cuda', 'NVIDIA 加速（CUDA）'),
            )):
                label = QtWidgets.QLabel(title)
                state = QtWidgets.QLabel('检查中')
                button = QtWidgets.QPushButton('下载')
                button.setObjectName('ghost')
                button.setMinimumWidth(88)
                button.clicked.connect(lambda checked=False, v=variant: self._download_llama_engine(v))
                engine_grid.addWidget(label, row, 0)
                engine_grid.addWidget(state, row, 1)
                engine_grid.addWidget(button, row, 2)
                self.engine_status_labels[variant] = state
                self.engine_download_buttons[variant] = button
            engine_grid.setColumnStretch(0, 1)
            el.addLayout(engine_grid)
            self.btn_engine_cuda = self.engine_download_buttons['cuda']
            row_var = QtWidgets.QHBoxLayout()
            row_var.addWidget(QtWidgets.QLabel("用哪个引擎"))
            self.cmb_engine_variant = self._combo()
            row_var.addWidget(self.cmb_engine_variant, 1)
            el.addLayout(row_var)
            self._reload_engine_variants()
            self.cmb_engine_variant.currentIndexChanged.connect(self._on_engine_variant_changed)
            note_var = QtWidgets.QLabel(
                "引擎任选一种即可，无需全部下载。CPU 通用，显卡加速可选。更改在下一次翻译时生效；"
                "自动模式会选择可用引擎，显卡启动失败时尝试 CPU。")
            note_var.setWordWrap(True)
            note_var.setStyleSheet("font-size: 11px; color: rgba(150,158,175,0.92);")
            el.addWidget(note_var)
            row_md = QtWidgets.QHBoxLayout()
            b_dl = QtWidgets.QPushButton("检查推荐模型…")
            self.btn_llama_model = b_dl
            b_dl.setObjectName("ghost")
            b_dl.clicked.connect(self._download_llama_model)
            row_md.addWidget(b_dl)
            el.addLayout(row_md)
            self.llama_bar, self.lbl_llama_prog = self._make_progress(el)
            row_s = QtWidgets.QHBoxLayout()
            b_sp = QtWidgets.QPushButton("测速（翻译一句试试）")
            b_sp.setObjectName("ghost")
            b_sp.clicked.connect(self._speed_llamacpp)
            row_s.addWidget(b_sp)
            row_s.addStretch(1)
            el.addLayout(row_s)
            self.lbl_llama_result = QtWidgets.QLabel("")
            self.lbl_llama_result.setWordWrap(True)
            self.lbl_llama_result.setStyleSheet("font-size: 11px; color: rgba(160,220,170,0.95);")
            el.addWidget(self.lbl_llama_result)
            note_el = QtWidgets.QLabel("完全免安装：引擎和模型都放在软件文件夹里，用户不需要装 Ollama。"
                                       "首次运行需要加载模型，随后常驻内存。译文边生成边显示，速度取决于电脑性能。")
            note_el.setWordWrap(True)
            note_el.setStyleSheet("font-size: 11px; color: rgba(150,158,175,0.92);")
            el.addWidget(note_el)
            lay.addWidget(self.llama_box)

            self.speed_llama.connect(self._on_speed_llama)
            self.eng_progress.connect(self._on_eng_progress)
            self.eng_finished.connect(self._on_eng_finished)
            self._on_provider_changed(None, init=True)
            box2 = QtWidgets.QCheckBox("边识别边翻译（更实时，消耗略高）")
            box2.setChecked(bool(self.cfg.get("translate.live", True)))
            self._bind_check(box2, "translate.live")
            lay.addWidget(box2)
            line_live = self._row(lay, "草稿译文",
                                  "草稿与整句使用当前选定的同一翻译服务，避免中途切换。")
            self.cmb_live_prov = self._combo()
            self.cmb_live_prov.addItem("自动", "auto")
            self.cmb_live_prov.addItem("与整句相同（推荐）", "same")
            i = self.cmb_live_prov.findData(str(self.cfg.get("translate.live_provider", "auto")))
            self.cmb_live_prov.setCurrentIndex(max(0, i))
            self._bind_combo(self.cmb_live_prov, "translate.live_provider")
            line_live.addWidget(self.cmb_live_prov, 1)

            # 将原先隐藏在 config.json / pipeline.py 中的四项节奏参数
            # 暴露给用户。初始值来自当前配置，创建控件不会覆盖用户已有设置。
            advanced = (
                ("实时请求间隔", "translate.live_min_interval_ms", 100, 10000, 450, 50, " ms",
                 "两次草稿翻译请求的最短间隔；实际还会根据翻译耗时自动放慢。",
                 "spn_live_interval"),
                ("新增字符门槛", "translate.live_min_new_chars", 1, 40, 2, 1, " 字",
                 "自上次请求至少新增多少日语字符，才允许发起下一次草稿翻译。",
                 "spn_live_chars"),
                ("上下文句数", "translate.context_lines", 0, 8, 3, 1, " 句",
                 "向翻译模型提供多少条以前的日语原文；设为 0 则不带上下文。",
                 "spn_context_lines"),
                ("最终字幕刷新", "translate.final_stream_interval_ms", 20, 1000, 40, 20, " ms",
                 "最终中文译文在生成过程中的最短推送间隔，增大可减少频繁刷新。"
                 "最后完整译文始终立即显示，不受此间隔限制。",
                 "spn_final_stream_interval"),
            )
            for label, path, low, high, default, step, suffix, tooltip, attr in advanced:
                setting_row = self._row(lay, label, tooltip)
                spin = QtWidgets.QSpinBox()
                spin.setRange(low, high)
                spin.setSingleStep(step)
                spin.setSuffix(suffix)
                spin.setValue(int(self.cfg.get(path, default)))
                spin.setToolTip(tooltip)
                spin.setMinimumWidth(130)
                spin.valueChanged.connect(lambda value, key=path: self._set(key, int(value), None))
                setattr(self, attr, spin)
                setting_row.addWidget(spin)

            fallback = QtWidgets.QCheckBox("翻译失败时，允许尝试其他免密钥在线服务")
            fallback.setChecked(bool(self.cfg.get("translate.auto_fallback", False)))
            self._bind_check(fallback, "translate.auto_fallback")
            lay.addWidget(fallback)

            # 术语表
            line3 = self._row(lay, "术语表", "固定一些昵称/专有名词的译法，例如 ぺこら→佩克拉")
            self.tbl = QtWidgets.QTableWidget(0, 2)
            self.tbl.setHorizontalHeaderLabels(["日语", "中文"])
            self.tbl.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
            self.tbl.verticalHeader().setVisible(False)
            self.tbl.setFixedHeight(120)
            for a, b in (self.cfg.get("translate.glossary", []) or []):
                r = self.tbl.rowCount()
                self.tbl.insertRow(r)
                self.tbl.setItem(r, 0, QtWidgets.QTableWidgetItem(str(a)))
                self.tbl.setItem(r, 1, QtWidgets.QTableWidgetItem(str(b)))
            self.tbl.itemChanged.connect(lambda _it: self._save_glossary())
            lay.addWidget(self.tbl)
            row3 = QtWidgets.QHBoxLayout()
            b_add = QtWidgets.QPushButton("+ 添加")
            b_add.setObjectName("ghost")
            b_del = QtWidgets.QPushButton("删除选中")
            b_del.setObjectName("ghost")
            b_add.clicked.connect(lambda: self.tbl.insertRow(self.tbl.rowCount()))
            b_del.clicked.connect(self._del_glossary_row)
            row3.addWidget(b_add)
            row3.addWidget(b_del)
            row3.addStretch(1)
            lay.addLayout(row3)

        def _save_glossary(self) -> None:
            items = []
            for r in range(self.tbl.rowCount()):
                a = self.tbl.item(r, 0)
                b = self.tbl.item(r, 1)
                a = a.text().strip() if a else ""
                b = b.text().strip() if b else ""
                if a and b:
                    items.append([a, b])
            self._set("translate.glossary", items, None)

        def _del_glossary_row(self) -> None:
            rows = sorted({i.row() for i in self.tbl.selectedIndexes()}, reverse=True)
            for r in rows:
                self.tbl.removeRow(r)
            self._save_glossary()

        def _on_provider_changed(self, _idx, init: bool = False) -> None:
            key = self.cmb_provider.currentData()
            if key not in TRANSLATE_PRESETS:
                key = "llamacpp"
            if not init:
                self.cfg.set("translate.provider", key)
                self.changed.emit("translate.provider", key)
            self.lbl_hint.setText(str(TRANSLATE_PRESETS[key].get("key_hint", "")))
            self.llama_box.setVisible(key == "llamacpp")
            if key == "llamacpp":
                self._refresh_llama_status()

        # ---- 界面外观 -------------------------------------------------------
        def _build_ui(self) -> None:
            lay = self._section("界面外观")

            line = self._row(lay, "主题")
            self.cmb_theme = self._combo()
            self.cmb_theme.addItem("深色（看直播更护眼）", "dark")
            self.cmb_theme.addItem("浅色", "light")
            idx = self.cmb_theme.findData(str(self.cfg.get("ui.theme", "dark")))
            self.cmb_theme.setCurrentIndex(max(0, idx))
            self._bind_combo(self.cmb_theme, "ui.theme")
            line.addWidget(self.cmb_theme, 1)

            self._row(lay, "强调色")
            sw = QtWidgets.QHBoxLayout()
            sw.setSpacing(6)
            cur_accent = str(self.cfg.get("ui.accent", "#ff86b3")).lower()
            for name, color in theme_mod.ACCENT_PRESETS:
                b = QtWidgets.QPushButton()
                b.setFixedSize(26, 26)
                b.setToolTip(name)
                ring = "3px solid rgba(255,255,255,0.85)" if color.lower() == cur_accent else "1px solid rgba(255,255,255,0.25)"
                b.setStyleSheet(f"QPushButton {{ background: {color}; border-radius: 13px; border: {ring}; }}")
                b.clicked.connect(lambda _c=False, col=color: self._pick_accent(col))
                sw.addWidget(b)
            b_custom = QtWidgets.QPushButton("自定义…")
            b_custom.setObjectName("ghost")
            b_custom.clicked.connect(self._custom_accent)
            sw.addWidget(b_custom)
            sw.addStretch(1)
            lay.addLayout(sw)

            self._row(lay, "背景照片", "内置均为真实摄影作品（免版权授权，非 AI 生成）；可点「选择图片」选自己的照片，或直接把图片拖进窗口")
            row_bg = QtWidgets.QHBoxLayout()
            self.bg_list = QtWidgets.QListWidget()
            self.bg_list.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
            self.bg_list.setIconSize(QtCore.QSize(96, 54))
            self.bg_list.setGridSize(QtCore.QSize(104, 84))
            self.bg_list.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
            self.bg_list.setMovement(QtWidgets.QListView.Movement.Static)
            self.bg_list.setFixedHeight(178)
            self.bg_list.itemClicked.connect(self._on_bg_pick)
            col_bg = QtWidgets.QVBoxLayout()
            b_pick = QtWidgets.QPushButton("选择图片…")
            b_pick.setObjectName("ghost")
            b_pick.clicked.connect(self.pick_background_file)
            b_open = QtWidgets.QPushButton("打开文件夹")
            b_open.setObjectName("ghost")
            b_open.clicked.connect(
                lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(BACKGROUNDS))))
            b_reload_bg = QtWidgets.QPushButton("↻ 刷新")
            b_reload_bg.setObjectName("ghost")
            b_reload_bg.clicked.connect(self._reload_backgrounds)
            col_bg.addWidget(b_pick)
            col_bg.addWidget(b_open)
            col_bg.addWidget(b_reload_bg)
            col_bg.addStretch(1)
            row_bg.addWidget(self.bg_list, 1)
            row_bg.addLayout(col_bg)
            lay.addLayout(row_bg)
            self._reload_backgrounds()

            for label, path, lo, hi in (
                ("背景模糊", "ui.bg_blur", 0, 40),
                ("背景暗度", "ui.bg_dim", 0, 90),
                ("背景不透明度", "ui.bg_opacity", 30, 100),
            ):
                r = self._row(lay, label)
                s = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
                s.setRange(lo, hi)
                s.setValue(int(self.cfg.get(path, (lo + hi) // 2)))
                lbl = QtWidgets.QLabel(str(s.value()))
                lbl.setFixedWidth(34)
                s.valueChanged.connect(lambda v, p=path, L=lbl: (L.setText(str(v)), self._set(p, int(v), None)))
                r.addWidget(s, 1)
                r.addWidget(lbl)

            r_font = self._row(lay, "字体")
            self.cmb_font = self._combo()
            cur_font = str(self.cfg.get("ui.font", "系统默认"))
            fonts = list(theme_mod.FONT_PRESETS)
            if cur_font and cur_font not in fonts:
                fonts.insert(1, cur_font)
            for f in fonts:
                self.cmb_font.addItem(f, "" if f == "系统默认" else f)
            i = self.cmb_font.findText(cur_font)
            self.cmb_font.setCurrentIndex(max(0, i))
            self._bind_combo(self.cmb_font, "ui.font")
            r_font.addWidget(self.cmb_font, 1)

            for label, path, lo, hi in (
                ("日语字号", "ui.jp_size", 10, 28),
                ("译文字号", "ui.zh_size", 12, 40),
            ):
                r = self._row(lay, label)
                sp = QtWidgets.QSpinBox()
                sp.setRange(lo, hi)
                sp.setValue(int(self.cfg.get(path, lo)))
                sp.valueChanged.connect(lambda v, p=path: self._set(p, int(v), None))
                r.addWidget(sp)

            r = self._row(lay, "内存保留字幕数", "包括日语原文和中文译文；超过数量立即丢弃，不可通过历史或导出恢复")
            self.spn_history_limit = QtWidgets.QSpinBox()
            self.spn_history_limit.setObjectName("history_limit")
            self.spn_history_limit.setRange(1, 1000)
            self.spn_history_limit.setSuffix(" 条")
            self.spn_history_limit.setToolTip("默认 3 条；修改后立即移除超过数量的旧字幕。")
            self.spn_history_limit.setValue(max(1, min(1000, int(self.cfg.get("ui.history_limit", 3)))))
            self.spn_history_limit.valueChanged.connect(
                lambda n: self._set("ui.history_limit", int(n), None))
            r.addWidget(self.spn_history_limit)

            r_disp = self._row(lay, "显示模式")
            self.cmb_display = self._combo()
            self.cmb_display.addItem("双语（原文+译文）", "both")
            self.cmb_display.addItem("只看译文", "zh")
            self.cmb_display.addItem("只看原文", "jp")
            i = self.cmb_display.findData(str(self.cfg.get("ui.display", "both")))
            self.cmb_display.setCurrentIndex(max(0, i))
            self._bind_combo(self.cmb_display, "ui.display")
            r_disp.addWidget(self.cmb_display, 1)

        def _pick_accent(self, color: str) -> None:
            self._set("ui.accent", color, None)

        def _custom_accent(self) -> None:
            c = QtWidgets.QColorDialog.getColor(QtGui.QColor(str(self.cfg.get("ui.accent", "#ff86b3"))), self)
            if c.isValid():
                self._set("ui.accent", c.name(), None)

        def _reload_backgrounds(self) -> None:
            self.bg_list.clear()
            cur = str(self.cfg.get("ui.bg", "auto"))
            chosen = resolve_background(cur) if cur else None

            def make_icon(path) -> QtGui.QIcon:
                pm = QtGui.QPixmap(str(path))
                if pm.isNull():
                    return QtGui.QIcon()
                pm = pm.scaled(192, 108, QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                               QtCore.Qt.TransformationMode.SmoothTransformation)
                x = max(0, (pm.width() - 192) // 2)
                y = max(0, (pm.height() - 108) // 2)
                return QtGui.QIcon(pm.copy(x, y, 192, 108))

            item_none = QtWidgets.QListWidgetItem("无背景")
            item_none.setData(QtCore.Qt.ItemDataRole.UserRole, "")
            self.bg_list.addItem(item_none)
            for f in background_files():
                item = QtWidgets.QListWidgetItem(make_icon(f), f.stem[:14])
                item.setData(QtCore.Qt.ItemDataRole.UserRole, f.name)
                item.setToolTip(f.name)
                self.bg_list.addItem(item)
                if chosen is not None and f == chosen:
                    self.bg_list.setCurrentItem(item)

        def _on_bg_pick(self, item: QtWidgets.QListWidgetItem) -> None:
            self._set("ui.bg", item.data(QtCore.Qt.ItemDataRole.UserRole), None)

        # ---- 自定义背景照片 ---------------------------------------------------
        def pick_background_file(self) -> None:
            path, _f = QtWidgets.QFileDialog.getOpenFileName(
                self, "选择背景照片", "", "图片文件 (*.jpg *.jpeg *.png *.webp *.bmp)")
            if not path:
                return
            self.add_background_file(Path(path))

        def add_background_file(self, src: Path) -> None:
            """把用户选择的图片复制进背景库并立即应用。"""
            from PIL import Image

            src = Path(src)
            try:
                with Image.open(src) as im:
                    im.verify()
            except Exception:  # noqa: BLE001
                QtWidgets.QMessageBox.warning(self, "无法使用该图片", f"文件不是可识别的图片：\n{src}")
                return
            try:
                BACKGROUNDS.mkdir(parents=True, exist_ok=True)
                safe = re.sub(r"[^\w\-.一-龥]+", "_", src.stem)[:40] or "photo"
                dest = BACKGROUNDS / f"custom-{safe}{src.suffix.lower()}"
                shutil.copyfile(src, dest)
                self._reload_backgrounds()
                for i in range(self.bg_list.count()):
                    it = self.bg_list.item(i)
                    if it.data(QtCore.Qt.ItemDataRole.UserRole) == dest.name:
                        self.bg_list.setCurrentItem(it)
                        break
                self._set("ui.bg", dest.name, None)
            except Exception as e:  # noqa: BLE001
                QtWidgets.QMessageBox.warning(self, "复制图片失败", str(e))

        # ---- 悬浮字幕 -------------------------------------------------------
        def _build_overlay(self) -> None:
            lay = self._section("悬浮字幕窗")
            box = QtWidgets.QCheckBox("显示悬浮字幕（置顶，可盖在直播画面上）")
            box.setChecked(bool(self.cfg.get("overlay.enabled", False)))
            self._bind_check(box, "overlay.enabled")
            lay.addWidget(box)
            note = QtWidgets.QLabel("用法：拖动字幕窗移动位置；滚轮调整字号；双击切换鼠标穿透；悬停出现小按钮。")
            note.setWordWrap(True)
            note.setStyleSheet("font-size: 11px; color: rgba(150,158,175,0.9);")
            lay.addWidget(note)

            r = self._row(lay, "显示行数")
            sp = QtWidgets.QSpinBox()
            sp.setRange(1, 4)
            sp.setValue(int(self.cfg.get("overlay.lines", 2)))
            sp.valueChanged.connect(lambda v: self._set("overlay.lines", int(v), None))
            r.addWidget(sp)

            r2 = self._row(lay, "译文字号")
            sp2 = QtWidgets.QSpinBox()
            sp2.setRange(14, 60)
            sp2.setValue(int(self.cfg.get("overlay.zh_size", 24)))
            sp2.valueChanged.connect(lambda v: self._set("overlay.zh_size", int(v), None))
            r2.addWidget(sp2)

            r3 = self._row(lay, "字幕框透明度")
            s3 = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            s3.setRange(0, 100)      # 拖到 0 = 完全去掉灰框，只留文字
            s3.setValue(int(self.cfg.get("overlay.opacity", 85)))
            s3.valueChanged.connect(lambda v: self._set("overlay.opacity", int(v), None))
            r3.addWidget(s3, 1)
            note_bg = QtWidgets.QLabel(
                "拖到最左边（0）= 完全去掉灰框，只留字幕文字（会自动加黑色描边，叠在画面上也看得清）；"
                "背景颜色与字幕颜色可在本窗口顶部调整。")
            note_bg.setWordWrap(True)
            note_bg.setStyleSheet("font-size: 11px; color: rgba(150,158,175,0.9);")
            lay.addWidget(note_bg)

            c0 = QtWidgets.QCheckBox("文字加黑色描边（背景越透明越明显）")
            c0.setChecked(bool(self.cfg.get("overlay.text_shadow", True)))
            self._bind_check(c0, "overlay.text_shadow")
            lay.addWidget(c0)

            c_jp = QtWidgets.QCheckBox("显示日语原文（只影响悬浮字幕，主窗口照旧）")
            c_jp.setChecked(bool(self.cfg.get("overlay.show_jp", True)))
            self._bind_check(c_jp, "overlay.show_jp")
            lay.addWidget(c_jp)

            c1 = QtWidgets.QCheckBox("鼠标穿透（点不到字幕窗，方便操作直播间）")
            c1.setChecked(bool(self.cfg.get("overlay.click_through", False)))
            self._bind_check(c1, "overlay.click_through")
            self._overlay_through_check = c1
            lay.addWidget(c1)
            c2 = QtWidgets.QCheckBox("锁定位置")
            c2.setChecked(bool(self.cfg.get("overlay.locked", False)))
            self._overlay_lock_check = c2
            def change_lock(locked: bool) -> None:
                self._set("overlay.locked", locked, None)
                if not locked and c1.isChecked():
                    # 解锁后必须能拖动；从设置页解锁时顺手关闭鼠标穿透。
                    c1.setChecked(False)
            c2.toggled.connect(change_lock)
            lay.addWidget(c2)

        def sync_overlay_controls(self) -> None:
            for box, path in ((self._overlay_through_check, "overlay.click_through"),
                              (self._overlay_lock_check, "overlay.locked")):
                blocker = QtCore.QSignalBlocker(box)
                box.setChecked(bool(self.cfg.get(path, False)))
                del blocker

        # ---- 关于 -----------------------------------------------------------
        def _build_about(self) -> None:
            lay = self._section("关于与素材来源")
            from .. import __version__

            ver = QtWidgets.QLabel(f"译声实时翻译 v{__version__}")
            ver.setStyleSheet("color: rgba(215,222,235,0.95);")
            lay.addWidget(ver)

            self.lbl_models = QtWidgets.QLabel("")
            self.lbl_models.setWordWrap(True)
            self.lbl_models.setStyleSheet("font-size: 11px; color: rgba(180,188,205,0.95);")
            lay.addWidget(self.lbl_models)
            b = QtWidgets.QPushButton("重新检测模型")
            b.setObjectName("ghost")
            b.clicked.connect(self._check_models)
            lay.addWidget(b)
            self._check_models()

            credits = load_credits().get("files", {})
            if credits:
                lines = ["背景照片来源（真实摄影作品）："]
                for fname, info in credits.items():
                    lines.append(f"· {info.get('title', fname)} — {info.get('artist', '')}（{info.get('license', '')}）")
                lbl = QtWidgets.QLabel("\n".join(lines))
                lbl.setWordWrap(True)
                lbl.setStyleSheet("font-size: 11px; color: rgba(150,158,175,0.95);")
                lay.addWidget(lbl)

            tips = QtWidgets.QLabel("快捷键：F9 开始/停止聆听 · F10 显示/隐藏悬浮字幕 · Esc 关闭设置窗口")
            tips.setWordWrap(True)
            tips.setStyleSheet("font-size: 11px; color: rgba(150,158,175,0.95);")
            lay.addWidget(tips)

        def _check_models(self) -> None:
            rows = [
                ("日语高速识别 Parakeet", FinalASR.available("parakeet")),
                ("静音检测 silero_vad", (MODELS / "silero_vad.onnx").exists()),
            ]
            text = "本地模型状态：" + "  ".join(f"{'✅' if ok else '❌'}{name}" for name, ok in rows)
            self.lbl_models.setText(text)

        # ---- 内置引擎（llama.cpp） -------------------------------------------
        def _reload_engine_variants(self) -> None:
            """刷新「用哪个引擎」下拉框（列出已下载的引擎变体）。"""
            from ..core import llama_engine as le

            labels = {
                "cpu": "CPU（不用显卡 · 最通用）",
                "vulkan": "Vulkan（A 卡 / 核显 / N 卡都能用）",
                "cuda": "CUDA（N 卡专用 · 最快）",
            }
            cur = str(self.cfg.get("translate.services.llamacpp.variant", "auto") or "auto")
            self.cmb_engine_variant.blockSignals(True)
            self.cmb_engine_variant.clear()
            self.cmb_engine_variant.addItem("自动选择（显卡不可用时回退 CPU）", "auto")
            for v in le.VARIANTS:
                mark = "已安装" if le.installed(v) else "未安装"
                self.cmb_engine_variant.addItem(f"{mark} · {labels.get(v, v)}", v)
            idx = self.cmb_engine_variant.findData(cur)
            self.cmb_engine_variant.setCurrentIndex(idx if idx >= 0 else 0)
            self.cmb_engine_variant.blockSignals(False)

        def _on_engine_variant_changed(self, _i: int) -> None:
            from ..core import llama_engine as le

            v = str(self.cmb_engine_variant.currentData() or "")
            if not v:
                return
            self.cfg.set_service("llamacpp", variant=v)
            # 告知控制器只更换引擎变体，不能按“所有服务参数变化”误杀新引擎。
            self.changed.emit("translate.services.llamacpp.variant", v)
            if v == "auto":
                self.lbl_llama_result.setText("自动选择可用引擎；显卡启动失败时使用 CPU")
                return
            if le.installed(v):
                self.lbl_llama_result.setStyleSheet("font-size: 11px; color: #9fdcae;")
                self.lbl_llama_result.setText(f"已切换到 {v} 引擎（下一次翻译就生效）")
            else:
                self.lbl_llama_result.setStyleSheet("font-size: 11px; color: rgba(255,209,102,0.95);")
                self.lbl_llama_result.setText(f"已选 {v}，但本地还没下载：点上面的「下载引擎」按钮下载一下。")
            self._refresh_llama_status()

        def _refresh_llama_status(self) -> None:
            from ..core import llama_engine as le
            variants = le.installed_variants()
            self._reload_engine_variants()
            model = le.resolve_model(str(self.cfg.service('llamacpp').get('model') or ''))
            busy = self._llama_job is not None
            for variant, state in self.engine_status_labels.items():
                button = self.engine_download_buttons[variant]
                downloading = self._llama_job == 'engine:' + variant
                installed = le.installed(variant)
                incomplete = le.engine_dir(variant).is_dir() and any(le.engine_dir(variant).iterdir()) and not installed
                state.setText('下载中…' if downloading else '已安装' if installed else '文件不完整' if incomplete else '未安装')
                state.setStyleSheet('color: #7ddc9a;' if installed and not downloading else 'color: #ffd166;')
                button.setText('下载中…' if downloading else '已安装' if installed else '修复下载' if incomplete else '下载')
                button.setEnabled(not busy and not installed)
                button.setVisible(not installed or downloading)
                button.setToolTip('已安装，无需重复下载' if installed else '下载后才能使用此引擎')
                if variant == 'cuda' and not le.nvidia_available() and not installed:
                    button.setEnabled(False)
                    button.setToolTip('仅用于 NVIDIA 显卡；当前电脑请使用 CPU 或 Vulkan')
            if model:
                size = model.stat().st_size / (1024 ** 3)
                name = model.stem
                model_text = f'翻译模型：已安装 · {name}（{size:.2f} GB）'
            else:
                model_text = '翻译模型：未安装，请下载混元 Hy-MT2 7B'
            self.lbl_llama_status.setText(f'本地引擎：已安装 {len(variants)} 个（任选一个即可）\n' + model_text)
            self.lbl_llama_status.setToolTip(str(model) if model else '')
            self.lbl_llama_status.setStyleSheet('font-size: 11px; color: ' + ('#9fdcae;' if model and variants else '#ffd166;'))
            recommended = le.MODELS_LLM / le.RECOMMENDED_MODELS[0]['name'] if le.RECOMMENDED_MODELS else None
            ready = recommended is not None and le.valid_model(recommended)
            selected = ready and model is not None and recommended.resolve() == model.resolve()
            if self._llama_job == 'model':
                caption = '混元 Hy-MT2 · 下载中…'
            elif ready:
                caption = '混元 Hy-MT2 · 已安装' if selected else '使用已安装的混元 Hy-MT2'
            else:
                caption = '混元 Hy-MT2 · 未安装，点击下载（约 4.62 GB）'
            self.btn_llama_model.setText(caption)
            self.btn_llama_model.setEnabled(not busy and not ready and bool(le.RECOMMENDED_MODELS))

        def _download_llama_engine(self, variant: str) -> None:
            from ..core import llama_engine as le
            if self._llama_job is not None or le.installed(variant):
                return
            self._llama_job = 'engine:' + variant
            self._refresh_llama_status()
            self.llama_bar.show()
            self.llama_bar.setRange(0, 100)
            self.lbl_llama_prog.show()
            self.lbl_llama_prog.setText(f"开始下载引擎（{variant}）…")

            def work() -> None:
                from ..core import llama_engine as le

                try:
                    le.download_engine(variant, lambda s, d, t: self.eng_progress.emit(s, d, t))
                    self.eng_finished.emit(f"ENGINE:{variant}")
                except Exception as e:  # noqa: BLE001
                    self.eng_finished.emit("ERR:" + str(e))

            threading.Thread(target=work, daemon=True).start()

        def _download_llama_model(self) -> None:
            from ..core import llama_engine as le

            if not le.RECOMMENDED_MODELS or self._llama_job is not None:
                return
            item = le.RECOMMENDED_MODELS[0]
            ready = le.MODELS_LLM / item['name']
            if le.valid_model(ready):
                self._on_eng_finished('MODEL:' + str(ready))
                return
            self._llama_job = 'model'
            self._refresh_llama_status()
            self.llama_bar.show()
            self.llama_bar.setRange(0, 100)
            self.lbl_llama_prog.show()
            self.lbl_llama_prog.setText(f"开始下载 {item['name']} …")

            def work() -> None:
                try:
                    dst = le.download_model(item, lambda s, d, t: self.eng_progress.emit(s, d, t))
                    self.eng_finished.emit(f"MODEL:{dst}")
                except Exception as e:  # noqa: BLE001
                    self.eng_finished.emit("ERR:" + str(e))

            threading.Thread(target=work, daemon=True).start()

        def _on_eng_progress(self, status: str, done: int, total: int) -> None:
            if total > 1:
                pct = int(done * 100 / total)
                self.llama_bar.setRange(0, 100)
                self.llama_bar.setValue(min(100, pct))
                self.lbl_llama_prog.setText(f"{status} {pct}%（{done / 1048576:.0f}MB / {total / 1048576:.0f}MB）")
            else:
                self.llama_bar.setRange(0, 0)
                self.lbl_llama_prog.setText(status)

        def _on_eng_finished(self, result: str) -> None:
            self._llama_job = None
            self._refresh_llama_status()
            self.llama_bar.hide()
            self.lbl_llama_prog.hide()
            if result.startswith("ERR:"):
                self.lbl_llama_result.setStyleSheet("font-size: 11px; color: #ffb3b3;")
                self.lbl_llama_result.setText("失败：" + result[4:])
                return
            kind, _, payload = result.partition(":")
            if kind == "MODEL":
                self.cfg.set_service("llamacpp", model="models/llm/Hy-MT2-7B-Q4_K_M.gguf")
                self.changed.emit("translate.services", None)
                self.lbl_llama_result.setStyleSheet("font-size: 11px; color: #9fdcae;")
                self.lbl_llama_result.setText(
                    f"混元模型已就绪：{breakable(Path(payload).name)}（点「测速」立即验证）")
            else:
                self.lbl_llama_result.setStyleSheet("font-size: 11px; color: #9fdcae;")
                self.lbl_llama_result.setText(f"引擎（{breakable(payload)}）已就绪。")
            self._refresh_llama_status()

        def _speed_llamacpp(self) -> None:
            self.lbl_llama_result.setStyleSheet("font-size: 11px; color: rgba(180,188,205,0.95);")
            self.lbl_llama_result.setText("测速中：首次会启动引擎并加载模型（5~30 秒）…")

            def work() -> None:
                import time as _t

                from ..core import llama_engine as le
                from ..core.translate import LlamaCppProvider

                try:
                    svc = self.cfg.service("llamacpp")
                    model = le.resolve_model(str(svc.get("model") or ""))
                    if model is None:
                        raise RuntimeError("尚未选择 GGUF 模型")
                    variant = le.preferred_variant(self.cfg)
                    t0 = _t.perf_counter()
                    out = LlamaCppProvider(dict(svc, variant=variant)).translate(
                        'あのさ、昨日コンビニで買ったスイーツがめっちゃ美味しかったんだよね。', [], [])
                    self.speed_llama.emit(f"每句约 {_t.perf_counter() - t0:.1f} 秒：{out}")
                except Exception as e:  # noqa: BLE001
                    self.speed_llama.emit(f"测速失败：{e}")

            threading.Thread(target=work, daemon=True).start()

        def _on_speed_llama(self, text: str) -> None:
            self.lbl_llama_result.setStyleSheet(
                "font-size: 11px; color: #ffb3b3;" if text.startswith("测速失败") else
                "font-size: 11px; color: #9fdcae;")
            self.lbl_llama_result.setText(text)
# END MODULE: jpsub.ui.settings

# ======================================================================
# BEGIN MODULE: jpsub.ui.theme  (jpsub/ui/theme.py)
# ======================================================================
if False:  # 可阅读的源码区块（独立模块由上方加载器执行）
    # -*- coding: utf-8 -*-
    """配色与全局样式表。"""
    # __FUTURE_IMPORT__ from __future__ import annotations

    from ..paths import ASSETS

    PALETTES = {
        "dark": {
            "bg": "#14161c",
            "panel": "#1c1f27",
            "panel2": "#232734",
            "border": "#2c3140",
            "text": "#eef1f7",
            "muted": "#9aa3b5",
            "faint": "#6b7280",
            "titlebar": "#191c24",
            "scroll": "#39404f",
            "hover": "#2a2f3d",
        },
        "light": {
            "bg": "#f4f6fb",
            "panel": "#ffffff",
            "panel2": "#eef1f7",
            "border": "#d9dfeb",
            "text": "#1b2030",
            "muted": "#5b6478",
            "faint": "#8b93a7",
            "titlebar": "#ffffff",
            "scroll": "#c3cadd",
            "hover": "#e6ebf5",
        },
    }

    ACCENT_PRESETS = [
        ("樱花粉", "#ff86b3"),
        ("初音绿", "#3ddc97"),
        ("天依蓝", "#5aa9ff"),
        ("紫罗兰", "#a78bfa"),
        ("晚霞橙", "#ff9f5a"),
        ("赤红", "#ff6b6b"),
        ("青碧", "#2ec4b6"),
    ]

    FONT_PRESETS = [
        "系统默认",
        "Microsoft YaHei UI",
        "Yu Gothic UI",
        "Noto Sans JP",
        "Source Han Sans SC",
        "HarmonyOS Sans SC",
        "SimHei",
        "SimSun",
    ]


    def _clamp(v: float) -> int:
        return max(0, min(255, int(v)))


    def shade(color: str, factor: float) -> str:
        """factor>1 变亮，factor<1 变暗。"""
        c = color.lstrip("#")
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        if factor >= 1:
            r = _clamp(r + (255 - r) * (factor - 1))
            g = _clamp(g + (255 - g) * (factor - 1))
            b = _clamp(b + (255 - b) * (factor - 1))
        else:
            r, g, b = _clamp(r * factor), _clamp(g * factor), _clamp(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"


    def with_alpha(color: str, alpha: float) -> str:
        c = color.lstrip("#")
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        return f"rgba({r},{g},{b},{alpha:.2f})"


    QSS = """
    * { outline: none; }
    QWidget { color: @text; font-family: "@font"; }
    QToolTip {
        background: @panel2; color: @text; border: 1px solid @border;
        border-radius: 6px; padding: 6px 8px;
    }
    QFrame#card, QFrame#drawerCard {
        background: @panel; border: 1px solid @border; border-radius: 12px;
    }
    QFrame#titlebar { background: transparent; }
    QLabel#muted { color: @muted; }
    QLabel#faint { color: @faint; }
    QLabel#sectionTitle { color: @accentText; font-weight: 600; font-size: 13px; }
    QPushButton {
        background: @panel2; color: @text; border: 1px solid @border;
        border-radius: 9px; padding: 7px 14px;
    }
    QPushButton:hover { background: @hover; }
    QPushButton:pressed { background: @panel2; }
    QPushButton:disabled { color: @faint; }
    QPushButton#accent {
        background: @accent; color: @onAccent; border: none; font-weight: 600;
        padding: 9px 22px; border-radius: 10px;
    }
    QPushButton#accent:hover { background: @accentHover; }
    QPushButton#accent:disabled { background: @border; color: @faint; }
    QPushButton#ghost {
        background: transparent; border: 1px solid @border; color: @muted;
        border-radius: 9px; padding: 5px 10px;
    }
    QPushButton#ghost:hover { color: @text; background: @hover; }
    QPushButton#winBtn {
        background: transparent; border: none; border-radius: 8px;
        padding: 6px 10px; color: @muted;
    }
    QPushButton#winBtn:hover { background: @hover; color: @text; }
    QPushButton#closeBtn {
        background: transparent; border: none; border-radius: 8px;
        padding: 6px 10px; color: @muted;
    }
    QPushButton#closeBtn:hover { background: #e5484d; color: white; }
    QPushButton:checked {
        background: @accentSoft; border: 1px solid @accent; color: @text;
    }
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
        background: @panel2; border: 1px solid @border; border-radius: 8px;
        padding: 6px 9px; selection-background-color: @accent;
    }
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid @accent; }
    QComboBox::drop-down { border: none; width: 22px; }
    QComboBox QAbstractItemView {
        background: @panel; border: 1px solid @border; border-radius: 8px;
        selection-background-color: @accentSoft; selection-color: @text; padding: 4px;
    }
    QSlider::groove:horizontal { height: 5px; background: @border; border-radius: 3px; }
    QSlider::sub-page:horizontal { background: @accent; border-radius: 3px; }
    QSlider::handle:horizontal {
        background: white; border: 2px solid @accent; width: 14px; height: 14px;
        margin: -6px 0; border-radius: 9px;
    }
    QSlider::handle:horizontal:hover { background: @accentSoft; }
    QCheckBox { spacing: 8px; }
    QCheckBox::indicator {
        width: 17px; height: 17px; border-radius: 5px;
        border: 1px solid @border; background: @panel2;
    }
    QCheckBox::indicator:hover { border: 1px solid @accent; }
    QCheckBox::indicator:checked {
        background: @accent; border: 1px solid @accent;
        image: url("@assets/check.png");
    }
    QScrollArea { border: none; background: transparent; }
    QScrollBar:vertical { background: transparent; width: 9px; margin: 2px; }
    QScrollBar::handle:vertical { background: @scroll; border-radius: 4px; min-height: 30px; }
    QScrollBar::handle:vertical:hover { background: @accent; }
    QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
    QScrollBar:horizontal { background: transparent; height: 9px; margin: 2px; }
    QScrollBar::handle:horizontal { background: @scroll; border-radius: 4px; min-width: 30px; }
    QMenu { background: @panel; border: 1px solid @border; border-radius: 10px; padding: 6px; }
    QMenu::item { padding: 7px 22px; border-radius: 7px; }
    QMenu::item:selected { background: @accentSoft; }
    QTableWidget {
        background: @panel2; border: 1px solid @border; border-radius: 8px;
        gridline-color: @border;
    }
    QHeaderView::section { background: @panel; color: @muted; border: none; padding: 5px; }
    QGroupBox { border: 1px solid @border; border-radius: 10px; margin-top: 12px; padding-top: 8px; }
    QGroupBox::title { subcontrol-origin: margin; left: 12px; color: @muted; }
    """


    def build_qss(theme: str, accent: str, font_family: str) -> str:
        p = PALETTES.get(theme, PALETTES["dark"])
        return (
            QSS.replace("@font", font_family or "Microsoft YaHei UI")
            .replace("@assets", ASSETS.as_posix())
            .replace("@accentHover", shade(accent, 1.18))
            .replace("@accentSoft", with_alpha(accent, 0.22))
            .replace("@accentText", accent)
            .replace("@accent", accent)
            .replace("@onAccent", "#ffffff")
            .replace("@bg", p["bg"])
            .replace("@panel2", p["panel2"])
            .replace("@panel", p["panel"])
            .replace("@border", p["border"])
            .replace("@hover", p["hover"])
            .replace("@scroll", p["scroll"])
            .replace("@muted", p["muted"])
            .replace("@faint", p["faint"])
            .replace("@titlebar", p["titlebar"])
            .replace("@text", p["text"])
        )
# END MODULE: jpsub.ui.theme

# ======================================================================
# BEGIN MODULE: jpsub.ui.transcript  (jpsub/ui/transcript.py)
# ======================================================================
if False:  # 可阅读的源码区块（独立模块由上方加载器执行）
    # -*- coding: utf-8 -*-
    """字幕显示区：流式逐字浮现、整句校对、历史行。"""
    # __FUTURE_IMPORT__ from __future__ import annotations

    from PySide6 import QtCore, QtGui, QtWidgets

    from ..core.segment import Segment


    class TypingLabel(QtWidgets.QLabel):
        """逐字浮现的标签：目标文本增长时逐字显示，营造"边说边出字"效果。"""

        def __init__(self, parent=None):
            super().__init__(parent)
            self._target = ""
            self._shown = 0
            self._timer = QtCore.QTimer(self)
            self._timer.setInterval(16)
            self._timer.timeout.connect(self._tick)
            self.setText("")

        def set_target(self, text: str) -> None:
            text = text or ""
            if text == self._target:
                return
            shown = self._target[:self._shown]
            if not text.startswith(shown) or len(text) < self._shown:
                # 保留公共前缀，避免整行闪回
                cp = 0
                m = min(len(shown), len(text))
                while cp < m and shown[cp] == text[cp]:
                    cp += 1
                self._shown = cp
            self._target = text
            if self._shown >= len(text):
                self.setText(text)
                self._timer.stop()
                return
            if not self._timer.isActive():
                self._timer.start()

        def snap(self, text: str) -> None:
            self._target = text or ""
            self._shown = len(self._target)
            super().setText(self._target)
            self._timer.stop()

        def _tick(self) -> None:
            if self._shown >= len(self._target):
                self._timer.stop()
                return
            step = max(1, (len(self._target) - self._shown) // 10)
            self._shown = min(len(self._target), self._shown + step)
            super().setText(self._target[:self._shown])


    class LineWidget(QtWidgets.QWidget):
        """一条字幕：日语原文 + 中文译文。"""

        def __init__(self, seg: Segment, jp_size: int, zh_size: int, parent=None):
            super().__init__(parent)
            self.seg = seg
            self._jp_size = jp_size
            self._zh_size = zh_size
            lay = QtWidgets.QVBoxLayout(self)
            lay.setContentsMargins(2, 6, 2, 6)
            lay.setSpacing(3)
            self.jp = QtWidgets.QLabel(seg.jp or "")
            self.zh = TypingLabel()
            self.zh.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
            self.jp.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
            self.jp.setWordWrap(True)
            self.zh.setWordWrap(True)
            lay.addWidget(self.jp)
            lay.addWidget(self.zh)
            self._apply_sizes(jp_size, zh_size)
            self._apply_style()

        def _apply_style(self) -> None:
            self.jp.setStyleSheet("color: rgba(180,190,205,0.85);")
            self.zh.setStyleSheet("color: #ffffff; font-weight: 600;")

        def _apply_sizes(self, jp: int, zh: int) -> None:
            self._jp_size, self._zh_size = jp, zh
            f_jp = self.font()
            f_jp.setPointSize(max(9, jp))
            self.jp.setFont(f_jp)
            f_zh = self.font()
            f_zh.setPointSize(max(10, zh))
            self.zh.setFont(f_zh)

        def set_sizes(self, jp: int, zh: int) -> None:
            self._apply_sizes(jp, zh)

        def set_zh(self, text: str, typing: bool = True) -> None:
            # 空字符串是明确的“撤回失败的流式草稿”，必须清理屏幕及历史记录。
            text = text or ""
            self.seg.zh = text
            if typing:
                self.zh.set_target(text)
            else:
                self.zh.snap(text)

        def set_jp(self, text: str) -> None:
            self.seg.jp = text
            self.jp.setText(text)

        def apply_display(self, mode: str) -> None:
            self.jp.setVisible(mode in ("both", "jp"))
            self.zh.setVisible(mode in ("both", "zh"))

        def contextMenuEvent(self, e) -> None:
            menu = QtWidgets.QMenu(self)
            act_copy_jp = menu.addAction("复制日语原文")
            act_copy_zh = menu.addAction("复制中文译文")
            act_copy_both = menu.addAction("复制双语")
            act = menu.exec(e.globalPos())
            if act == act_copy_jp:
                QtWidgets.QApplication.clipboard().setText(self.seg.jp)
            elif act == act_copy_zh:
                QtWidgets.QApplication.clipboard().setText(self.seg.zh)
            elif act == act_copy_both:
                QtWidgets.QApplication.clipboard().setText(f"{self.seg.jp}\n{self.seg.zh}")


    class TranscriptView(QtWidgets.QScrollArea):
        """滚动字幕区：底部实时行 + 上方历史行。"""

        def __init__(self, cfg, parent=None):
            super().__init__(parent)
            self.cfg = cfg
            self.setWidgetResizable(True)
            self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
            self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            container = QtWidgets.QWidget()
            container.setObjectName("transcriptContainer")
            container.setStyleSheet("QWidget#transcriptContainer { background: transparent; }")
            self.vbox = QtWidgets.QVBoxLayout(container)
            self.vbox.setContentsMargins(6, 8, 10, 8)
            self.vbox.setSpacing(2)
            self.vbox.addStretch(1)
            self.setWidget(container)
            self.lines: list[LineWidget] = []
            self._map: dict[str, LineWidget] = {}
            # 唯一保留的完整字幕历史：严格受 ui.history_limit 限制。
            # 被淘汰的字幕/译文不可从历史窗口或导出功能恢复。
            self._history: list[Segment] = []
            self._history_by_sid: dict[str, Segment] = {}
            self._live: LineWidget | None = None
            # 一个清空内容的空闲控件供下句复用，避免高频 Qt 分配/销毁导致 RSS 膨胀。
            self._recycled: LineWidget | None = None
            jp = int(cfg.get("ui.jp_size", 13))
            zh = int(cfg.get("ui.zh_size", 19))
            self._sizes = (jp, zh)
            mode = str(cfg.get("ui.display", "both"))
            self._display = mode
            self.placeholder = QtWidgets.QLabel(
                "点击「开始聆听」后，这里会实时显示日语原文与中文翻译。\n"
                "先播放在看的直播，让声音从扬声器/耳机正常出声即可。\n"
                "默认使用随附的本地模型。需要调整字幕或使用云端翻译时，可打开「设置」。")
            self.placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.placeholder.setStyleSheet("color: rgba(200,208,220,0.55); font-size: 13px;")
            self.vbox.insertWidget(0, self.placeholder)

        # ------------------------------------------------------------- 控件复用
        def _take_line(self, seg: Segment) -> LineWidget:
            line = self._recycled
            self._recycled = None
            if line is None:
                line = LineWidget(seg, *self._sizes)
            else:
                line.seg = seg
                line.set_jp(seg.jp)
                line.show()
            line.set_zh(seg.zh, typing=False)
            return line

        def _recycle_line(self, line: LineWidget) -> None:
            self.vbox.removeWidget(line)
            line.hide()
            # snap 会停止正在运行的文字动画定时器。
            line.set_zh("", typing=False)
            line.set_jp("")
            line.seg = Segment(sid="", jp="")
            if self._recycled is None:
                self._recycled = line
            else:
                line.deleteLater()

        # ------------------------------------------------------------- 实时行
        def _ensure_live(self) -> LineWidget:
            if self._live is None:
                seg = Segment(sid="live", jp="")
                self._live = self._take_line(seg)
                self._live.apply_display(self._display)
                self.live_placeholder_hide()
                self.vbox.addWidget(self._live)
            return self._live

        def live_placeholder_hide(self) -> None:
            self.placeholder.setVisible(False)

        def set_live_jp(self, text: str) -> None:
            if not text:
                return
            line = self._ensure_live()
            line.jp.setText(text)
            line.seg.jp = text
            self._scroll_if_bottom()

        def set_live_zh(self, text: str) -> None:
            # 空内容是翻译流故障后的撤回通知；已有行必须清除，但不能凭空创建空行。
            if not text and self._live is None:
                return
            line = self._ensure_live()
            line.zh.snap(text or "")
            line.seg.zh = text or ""
            if text:
                self._scroll_if_bottom()

        def clear_live(self) -> None:
            """音频出现间断时丢弃未提交的临时字幕，不触及历史条目。"""
            if self._live is not None:
                line = self._live
                self._live = None
                self._recycle_line(line)

        # ------------------------------------------------------------- 整句
        def commit_segment(self, seg: Segment) -> LineWidget:
            """整句校对结果到达：把实时行定格为历史行。"""
            if self._live is not None:
                line = self._live
                line.seg.sid = seg.sid
                line.seg.t0, line.seg.t1 = seg.t0, seg.t1
                line.seg.rtf, line.seg.asr_seconds = seg.rtf, seg.asr_seconds
                line.seg.live_jp = seg.live_jp
                line.set_jp(seg.jp)
                line.zh.snap(line.seg.zh or "")
                self._live = None
            else:
                line = self._take_line(seg)
                line.apply_display(self._display)
                self.vbox.addWidget(line)
            line.set_sizes(*self._sizes)
            line.apply_display(self._display)
            self.lines.append(line)
            self._map[seg.sid] = line
            self._history.append(line.seg)
            self._history_by_sid[seg.sid] = line.seg
            self._trim()
            self._scroll_if_bottom(force=True)
            return line

        def set_zh_for(self, sid: str, text: str) -> None:
            saved = self._history_by_sid.get(sid)
            if saved is None:
                # 已淘汰条目的晚到翻译不能重新占用内存或回到 UI。
                return
            saved.zh = text or ""
            line = self._map.get(sid)
            if line is not None:
                line.set_zh(text, typing=False)
                self._scroll_if_bottom()

        # ------------------------------------------------------------- 外观
        def set_sizes(self, jp: int, zh: int) -> None:
            self._sizes = (jp, zh)
            for line in self.lines + ([self._live] if self._live else []):
                line.set_sizes(jp, zh)

        def set_display_mode(self, mode: str) -> None:
            self._display = mode
            for line in self.lines + ([self._live] if self._live else []):
                line.apply_display(mode)

        def set_max_lines(self) -> None:
            """保留数量减少时立即释放旧字幕；增大上限不会恢复已丢弃记录。"""
            self._trim()

        def clear_all(self) -> None:
            for line in self.lines:
                self.vbox.removeWidget(line)
                line.deleteLater()
            self.lines.clear()
            self._map.clear()
            self._history.clear()
            self._history_by_sid.clear()
            if self._recycled is not None:
                self._recycled.deleteLater()
                self._recycled = None
            if self._live is not None:
                self.vbox.removeWidget(self._live)
                self._live.deleteLater()
                self._live = None
            self.placeholder.setVisible(True)

        def _trim(self) -> None:
            keep = max(1, min(1000, int(self.cfg.get("ui.history_limit", 3))))
            # 历史数据、sid 索引和 UI 控件一起淘汰，不能只删除屏幕上的行。
            while len(self._history) > keep:
                old_seg = self._history.pop(0)
                self._history_by_sid.pop(old_seg.sid, None)
            while len(self.lines) > keep:
                old = self.lines.pop(0)
                self._map.pop(old.seg.sid, None)
                self._recycle_line(old)

        def _scroll_if_bottom(self, force: bool = False) -> None:
            bar = self.verticalScrollBar()
            near = bar.maximum() - bar.value() < 60
            if near or force:
                # Qt 以 self 为 context：字幕窗口销毁时自动丢弃待执行的回调。
                QtCore.QTimer.singleShot(0, self, self._scroll_to_bottom)

        def _scroll_to_bottom(self) -> None:
            bar = self.verticalScrollBar()
            bar.setValue(bar.maximum())

        def all_segments(self) -> list[Segment]:
            return list(self._history)

        def recent_segments(self, count: int) -> list[Segment]:
            return self._history[-max(1, count):]
# END MODULE: jpsub.ui.transcript

# ======================================================================
# BEGIN MODULE: jpsub.ui.window  (jpsub/ui/window.py)
# ======================================================================
if False:  # 可阅读的源码区块（独立模块由上方加载器执行）
    # -*- coding: utf-8 -*-
    """主窗口：标题栏 + 工具栏 + 字幕区 + 设置抽屉 + 悬浮字幕 + 托盘。"""
    # __FUTURE_IMPORT__ from __future__ import annotations

    import threading
    import time
    from pathlib import Path

    from PySide6 import QtCore, QtGui, QtWidgets

    from .. import APP_NAME, __version__
    from ..core.segment import Segment
    from ..paths import ASSETS, HISTORY
    from .background import BackgroundLayer
    from .overlay import OverlayWindow
    from .transcript import TranscriptView


    class LevelBar(QtWidgets.QWidget):
        """音量电平条。"""

        def __init__(self, parent=None):
            super().__init__(parent)
            self._level = 0.0
            self.setFixedSize(90, 8)

        def set_level(self, v: float) -> None:
            self._level = max(0.0, min(1.0, v))
            self.update()

        def paintEvent(self, e) -> None:
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            rect = self.rect()
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(QtGui.QColor(255, 255, 255, 38))
            p.drawRoundedRect(rect, 4, 4)
            w = int(rect.width() * self._level)
            if w > 2:
                grad = QtGui.QLinearGradient(0, 0, rect.width(), 0)
                grad.setColorAt(0.0, QtGui.QColor("#4fd08a"))
                grad.setColorAt(0.7, QtGui.QColor("#ffd166"))
                grad.setColorAt(1.0, QtGui.QColor("#ff6b6b"))
                p.setBrush(QtGui.QBrush(grad))
                p.drawRoundedRect(QtCore.QRect(0, 0, w, rect.height()), 4, 4)


    class _EngineStopScheduler:
        """串行合并 GPU/CPU 引擎切换，绝不在 GUI 线程等待 llama-server。

        多次快速改设置时只处理当前进行的一次和最后选定的版本；后台执行只
        操作引擎管理器，不访问任何 Qt 控件或用户配置文件。
        """

        def __init__(self):
            self._lock = threading.Lock()
            self._requested: tuple[str | None] | None = None
            self._worker: threading.Thread | None = None
            self._idle = threading.Event()
            self._idle.set()
            self.last_error = ""

        def request(self, keep_variant: str | None) -> None:
            with self._lock:
                self._requested = (keep_variant,)
                self._idle.clear()
                if self._worker is None:
                    self._worker = threading.Thread(
                        target=self._drain, name="YishengTranslator-engine-switch",
                        daemon=True)
                    self._worker.start()

        def _drain(self) -> None:
            from ..core.llama_engine import stop_translation

            while True:
                with self._lock:
                    if self._requested is None:
                        self._worker = None
                        self._idle.set()
                        return
                    (keep_variant,) = self._requested
                    self._requested = None
                try:
                    stop_translation(keep_variant=keep_variant)
                except Exception as exc:  # noqa: BLE001
                    # 不允许后台异常杀掉整个设置界面；异常保留供诊断。
                    self.last_error = str(exc)

        def wait(self, timeout: float = 2.0) -> bool:
            """主要用于单元/集成测试及安全诊断。"""
            return self._idle.wait(timeout)


    class MainWindow(QtWidgets.QWidget):
        def __init__(self, cfg):
            super().__init__(None)
            self.cfg = cfg
            self.pipeline: Pipeline | None = None
            self._retiring_pipelines = []
            # Retain QObjects while an uninterruptible native model call winds down.
            self._orphaned_pipelines = []
            self._orphan_timer = QtCore.QTimer(self)
            self._orphan_timer.setInterval(100)
            self._orphan_timer.timeout.connect(self._reap_orphaned)
            self._restart_requested = False
            self.overlay: OverlayWindow | None = None
            self._settings = None
            self._settings_dialog = None
            self._boot_done = False
            self._ui_ready = False  # 初始化期间不弹提示气泡
            self._closing = False
            self._overlay_only = False  # 主界面当前是否隐藏
            self._overlay_is_primary = False  # 会话是否由字幕模式启动：主界面的 X 仅隐藏
            self._quit_requested = False     # 只有明确的退出命令才能关闭后台模型与流水线
            self._engine_stop_scheduler = _EngineStopScheduler()
            self._quit_cleanup_done = threading.Event()
            self._quit_cleanup_thread: threading.Thread | None = None
            self._quit_cleanup_error = ""
            self._quit_poll: QtCore.QTimer | None = None
            self._config_warning: QtWidgets.QMessageBox | None = None
            self._live_jp = ""
            self._live_zh = ""
            self._drag_pos: QtCore.QPoint | None = None
            self._resize_edges = ""
            self._resize_start: tuple | None = None
            self._session_start = 0.0

            self.setWindowTitle(APP_NAME)
            self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint
                                | QtCore.Qt.WindowType.Window)
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setMinimumSize(880, 560)
            icon_path = ASSETS / "icon.png"
            if icon_path.exists():
                self.setWindowIcon(QtGui.QIcon(str(icon_path)))
            self.setAcceptDrops(True)  # 支持把图片拖进窗口换背景

            # 背景层
            self.bg = BackgroundLayer(self)
            self.bg.setGeometry(self.rect())
            # 内容
            self._build_ui()
            self._apply_theme()
            self._restore_geometry()
            self._build_tray()
            self._install_shortcuts()
            self.bg.lower()
            self.btn_ontop.setChecked(bool(self.cfg.get("ui.window.on_top", False)))
            self.btn_overlay.setChecked(bool(self.cfg.get("overlay.enabled", False)))
            self._update_trans_label_from_cfg()
            self._ui_ready = True

        def notify_config_failure(self) -> bool:
            """Non-modal warning; never silently overwrite a malformed config."""
            if not self.cfg.load_error:
                return False
            if self._config_warning is not None:
                self._config_warning.raise_()
                return True
            box = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Icon.Warning,
                "译声配置文件读取失败",
                f"配置文件：{self.cfg.path}\n\n"
                "已阻止自动保存和自动开始聆听。原始配置没有被覆盖。",
                QtWidgets.QMessageBox.StandardButton.Ok,
            )
            box.setInformativeText(
                "请先备份损坏的配置文件，再手动修复 JSON；"
                "或关闭程序后将其移走，重新启动以使用新配置。"
            )
            box.setDetailedText(self.cfg.load_error)
            box.setWindowModality(QtCore.Qt.WindowModality.NonModal)
            box.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, True)
            self._config_warning = box
            box.finished.connect(lambda _code: setattr(self, "_config_warning", None))
            box.show()
            self._on_status("配置文件损坏，请先处理配置文件")
            return True

        # ==================================================================
        def _build_ui(self) -> None:
            outer = QtWidgets.QVBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(0)

            # ---- 标题栏
            self.titlebar = QtWidgets.QFrame()
            self.titlebar.setObjectName("titlebar")
            self.titlebar.setFixedHeight(42)
            tb = QtWidgets.QHBoxLayout(self.titlebar)
            tb.setContentsMargins(16, 6, 10, 2)
            tb.setSpacing(6)
            self.lbl_logo = QtWidgets.QLabel()
            logo_pm = QtGui.QPixmap(str(ASSETS / "icon.png"))
            if logo_pm.isNull():
                self.lbl_logo.setText("🌸")
            else:
                self.lbl_logo.setPixmap(logo_pm.scaled(
                    20, 20, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation))
                self.lbl_logo.setFixedWidth(24)
            self.lbl_title = QtWidgets.QLabel(APP_NAME)
            self.lbl_title.setStyleSheet("font-weight: 700; font-size: 15px;")
            tb.addWidget(self.lbl_logo)
            tb.addWidget(self.lbl_title)
            tb.addStretch(1)
            self.btn_overlay = self._win_btn("⬒ 悬浮字幕", "悬浮字幕窗（F10）", checkable=True)
            self.btn_ontop = self._win_btn("📌 置顶", "窗口置顶", checkable=True)
            self.btn_settings = self._win_btn("⚙ 设置", "打开/关闭字幕与翻译设置窗口", checkable=True)
            self.btn_min = self._win_btn("─", "最小化")
            self.btn_close = self._win_btn("✕", "退出", close=True)
            for b in (self.btn_overlay, self.btn_ontop, self.btn_settings,
                      self.btn_min, self.btn_close):
                tb.addWidget(b)
            outer.addWidget(self.titlebar)

            # 提示气泡（须在按钮状态初始化之前创建）
            self.toast = QtWidgets.QLabel("", self)
            self.toast.setObjectName("card")
            self.toast.setWordWrap(True)          # 提示里有「哪个服务不可用」这类长句，换行才不会超出窗口
            self.toast.setMaximumWidth(620)
            self.toast.setStyleSheet(
                "background: rgba(20,22,30,0.92); border: 1px solid rgba(255,255,255,0.12);"
                "border-radius: 10px; padding: 8px 14px; color: white;"
            )
            self.toast.hide()
            self._toast_timer = QtCore.QTimer(self)
            self._toast_timer.setSingleShot(True)
            self._toast_timer.timeout.connect(self.toast.hide)

            # ---- 主体
            body = QtWidgets.QHBoxLayout()
            body.setContentsMargins(16, 0, 16, 0)
            body.setSpacing(12)
            outer.addLayout(body, 1)

            left = QtWidgets.QVBoxLayout()
            left.setSpacing(10)
            body.addLayout(left, 1)

            # 两行工具栏：打开设置抽屉、缩小窗口时，设备和操作按钮仍可点。
            bar = QtWidgets.QVBoxLayout()
            bar.setSpacing(5)
            primary = QtWidgets.QHBoxLayout()
            primary.setSpacing(8)
            secondary = QtWidgets.QHBoxLayout()
            secondary.setSpacing(6)
            self.btn_start = QtWidgets.QPushButton("▶  开始聆听")
            self.btn_start.setObjectName("accent")
            self.btn_start.setFixedHeight(40)
            self.btn_start.setMinimumWidth(150)
            self.btn_start.clicked.connect(self.toggle_start)
            primary.addWidget(self.btn_start)
            self.lbl_state = QtWidgets.QLabel("● 未开始")
            self.lbl_state.setStyleSheet("color: rgba(190,198,215,0.9);")
            primary.addWidget(self.lbl_state)
            primary.addStretch(1)
            self.cmb_device = QtWidgets.QComboBox()
            self.cmb_device.setMinimumWidth(180)
            self.cmb_device.setMaximumWidth(220)
            self.cmb_device.setToolTip("快速切换要监听的声音设备")
            self.cmb_device.addItem("默认输出设备", "")
            secondary.addWidget(self.cmb_device)
            secondary.addStretch(1)
            self.btn_clear = QtWidgets.QPushButton("清空")
            self.btn_clear.setObjectName("ghost")
            self.btn_clear.clicked.connect(self._clear)
            self.btn_history = QtWidgets.QPushButton("保留记录")
            self.btn_history.setObjectName("ghost")
            self.btn_history.setToolTip("仅查看当前内存中保留的最近字幕；超出保留数量的旧记录已销毁")
            self.btn_history.clicked.connect(self._show_history)
            self.btn_export = QtWidgets.QPushButton("导出字幕")
            self.btn_export.setObjectName("ghost")
            self.btn_export.clicked.connect(self._export)
            secondary.addWidget(self.btn_clear)
            secondary.addWidget(self.btn_history)
            secondary.addWidget(self.btn_export)
            bar.addLayout(primary)
            bar.addLayout(secondary)
            left.addLayout(bar)

            # 字幕区
            self.transcript = TranscriptView(self.cfg)
            left.addWidget(self.transcript, 1)

            # 底部状态
            foot = QtWidgets.QHBoxLayout()
            foot.setSpacing(14)
            self.lbl_engine = QtWidgets.QLabel("引擎：未加载")
            self.lbl_engine.setObjectName("faint")
            self.lbl_trans = QtWidgets.QLabel("翻译：-")
            self.lbl_trans.setObjectName("faint")
            self.lbl_stats = QtWidgets.QLabel("")
            self.lbl_stats.setObjectName("faint")
            self.level = LevelBar()
            foot.addWidget(self.lbl_engine)
            foot.addWidget(self.lbl_trans)
            foot.addWidget(self.lbl_stats)
            foot.addStretch(1)
            foot.addWidget(QtWidgets.QLabel("音量"))
            foot.addWidget(self.level)
            left.addLayout(foot)

            # ---- 设置抽屉
            self.drawer_frame = QtWidgets.QFrame()
            self.drawer_frame.setObjectName("drawerCard")
            self._drawer_layout = QtWidgets.QVBoxLayout(self.drawer_frame)
            self._drawer_layout.setContentsMargins(4, 6, 4, 6)
            self.drawer_frame.setMaximumWidth(0)
            self.drawer_frame.setMinimumWidth(0)
            body.addWidget(self.drawer_frame)

            outer.addSpacing(12)

            # 连接按钮
            self.btn_settings.toggled.connect(self.toggle_drawer)
            self.btn_ontop.toggled.connect(self._toggle_ontop)
            self.btn_overlay.toggled.connect(self._toggle_overlay)
            self.btn_min.clicked.connect(self.showMinimized)
            self.btn_close.clicked.connect(self.close)

        def _win_btn(self, text: str, tip: str, checkable: bool = False, close: bool = False) -> QtWidgets.QPushButton:
            b = QtWidgets.QPushButton(text)
            b.setObjectName("closeBtn" if close else "winBtn")
            b.setToolTip(tip)
            b.setCheckable(checkable)
            if close or text in ("─",):
                b.setFixedWidth(38)
            return b

        # ==================================================================
        def _apply_theme(self) -> None:
            from .theme import build_qss

            theme = str(self.cfg.get("ui.theme", "dark"))
            accent = str(self.cfg.get("ui.accent", "#ff86b3"))
            font = str(self.cfg.get("ui.font", "系统默认"))
            app = QtWidgets.QApplication.instance()
            f = app.font()
            if font and font != "系统默认":
                f.setFamily(font)
            app.setFont(f)
            app.setStyleSheet(build_qss(theme, accent, f.family()))
            self.lbl_title.setStyleSheet("font-weight: 700; font-size: 15px; color: " +
                                         ("white" if theme == "dark" else "#1b2030") + ";")

        def _apply_bg(self) -> None:
            self.bg.set_background(
                str(self.cfg.get("ui.bg", "auto")),
                int(self.cfg.get("ui.bg_blur", 16)),
                int(self.cfg.get("ui.bg_dim", 45)),
                int(self.cfg.get("ui.bg_opacity", 100)),
                animate=False,
            )

        def _schedule_bg_apply(self, delay_ms: int = 180) -> None:
            """背景模糊/暗度这类滑条一拖就是几十次改动，等手停下来再重算背景图。

            否则每动一格都要重新模糊一张全屏照片，界面就一顿一顿的。
            """
            if not hasattr(self, "_bg_timer"):
                self._bg_timer = QtCore.QTimer(self)
                self._bg_timer.setSingleShot(True)
                self._bg_timer.timeout.connect(self._apply_bg)
            self._bg_timer.start(max(0, int(delay_ms)))

        def _restore_geometry(self) -> None:
            w = int(self.cfg.get("ui.window.w", 1100))
            h = int(self.cfg.get("ui.window.h", 700))
            x, y = self.cfg.get("ui.window.x"), self.cfg.get("ui.window.y")
            self.resize(w, h)
            screens = QtWidgets.QApplication.screens()
            rect = QtCore.QRect(int(x), int(y), w, h) if x is not None and y is not None else QtCore.QRect()
            if x is not None and y is not None and any(s.availableGeometry().intersects(rect) for s in screens):
                self.move(int(x), int(y))
            else:
                screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
                self.move(screen.center() - QtCore.QPoint(w // 2, h // 2 + 40))

        # ==================================================================
        def _refresh_devices(self) -> None:
            from ..core import audio as audio_mod

            self.cmb_device.blockSignals(True)
            self.cmb_device.clear()
            self.cmb_device.addItem("默认输出设备", "")
            devs = audio_mod.list_devices()
            src = str(self.cfg.get("audio.source", "loopback"))
            for name in devs.get("mic" if src == "mic" else "loopback", []):
                self.cmb_device.addItem(name, name)
            cur = str(self.cfg.get("audio.device", "") or "")
            idx = self.cmb_device.findData(cur)
            self.cmb_device.setCurrentIndex(max(0, idx))
            self.cmb_device.blockSignals(False)
            if not getattr(self, "_device_signal_bound", False):
                self.cmb_device.currentIndexChanged.connect(self._on_device_quick)
                self._device_signal_bound = True

        def _on_device_quick(self, _i: int) -> None:
            self.cfg.set("audio.device", self.cmb_device.currentData())
            self._on_setting_changed("audio.device", None)

        # ==================================================================
        @property
        def settings(self):
            """Local live-caption 风格：独立、可移动的设置窗口，保留全部高级设置。"""
            if self._settings is None:
                from .settings import SettingsPanel

                dlg = QtWidgets.QDialog(self, QtCore.Qt.WindowType.Window)
                dlg.setWindowTitle("译声 · 字幕与翻译设置")
                dlg.setObjectName("captionSettingsDialog")
                # 原程序全局采用深色字体样式；独立对话框必须有匹配背景，避免白底白字。
                dlg.setStyleSheet("QDialog#captionSettingsDialog { background: #1c1f27; }")
                dlg.setMinimumSize(480, 520)
                dlg.resize(590, 760)
                layout = QtWidgets.QVBoxLayout(dlg)
                layout.setContentsMargins(18, 16, 18, 12)
                layout.setSpacing(10)
                title = QtWidgets.QLabel("字幕与翻译设置")
                title.setStyleSheet("font-size: 19px; font-weight: 700;")
                layout.addWidget(title)
                tip = QtWidgets.QLabel("修改后立即预览并自动保存；字幕条与设置窗口互不遮挡。")
                tip.setStyleSheet("color: #9aa3b5; font-size: 12px;")
                tip.setWordWrap(True)
                layout.addWidget(tip)
                self._settings = SettingsPanel(self.cfg, dlg)
                self._settings.changed.connect(self._on_setting_changed)
                layout.addWidget(self._settings, 1)
                actions = QtWidgets.QHBoxLayout()
                actions.addStretch()
                done = QtWidgets.QPushButton("保存并关闭")
                done.setObjectName("accent")
                done.clicked.connect(dlg.close)
                actions.addWidget(done)
                layout.addLayout(actions)
                dlg.finished.connect(
                    lambda _: self.btn_settings.setChecked(False) if self.btn_settings.isChecked() else None)
                self._settings_dialog = dlg
            return self._settings

        def showEvent(self, e: QtGui.QShowEvent) -> None:
            super().showEvent(e)
            if not self._boot_done:
                self._boot_done = True
                # 先把窗口显示出来，再做背景照片、设备列表这些稍费时的收尾
                QtCore.QTimer.singleShot(0, self._deferred_init)

        def _deferred_init(self) -> None:
            self._apply_bg()
            self._refresh_devices()

        def toggle_drawer(self, on: bool) -> None:
            """保留旧接口名称，改为显示或隐藏独立设置窗口。"""
            if on:
                self.settings
                self._settings_dialog.show()
                self._settings_dialog.raise_()
                self._settings_dialog.activateWindow()
            elif self._settings_dialog is not None:
                self._settings_dialog.hide()

        def _get_drawer_width(self) -> int:
            return self.drawer_frame.maximumWidth()

        def _set_drawer_width(self, w: int) -> None:
            w = max(0, int(w))
            self.drawer_frame.setMinimumWidth(w)
            self.drawer_frame.setMaximumWidth(w)

        drawerWidth = QtCore.Property(int, _get_drawer_width, _set_drawer_width)

        def drawer_width(self) -> int:
            """抽屉该多宽：按设置面板内容实际需要的宽度算，别让右边的内容被裁掉。"""
            need = 402
            panel = self._settings
            if panel is not None:
                inner = panel.widget()
                if inner is not None:
                    need = max(need, inner.minimumSizeHint().width() + 40)
            limit = max(402, self.width() - 420)   # 给左边的字幕区留出合理宽度
            return max(402, min(need, limit))

        def _toggle_ontop(self, on: bool) -> None:
            self.cfg.set("ui.window.on_top", bool(on))
            flags = self.windowFlags()
            if on:
                flags |= QtCore.Qt.WindowType.WindowStaysOnTopHint
            else:
                flags &= ~QtCore.Qt.WindowType.WindowStaysOnTopHint
            self.setWindowFlags(flags)
            self.show()
            if self._ui_ready:
                self.toast_msg("窗口已置顶（再次点「置顶」可取消）" if on else "已取消窗口置顶")

        def _ensure_overlay(self) -> OverlayWindow:
            if self.overlay is None:
                self.overlay = OverlayWindow(self.cfg)
                self.overlay.interaction_changed.connect(
                    lambda: self._settings.sync_overlay_controls() if self._settings else None)
                self.overlay.settings_requested.connect(
                    lambda: self.btn_settings.setChecked(True)
                    if not self.btn_settings.isChecked() else self.toggle_drawer(True))
                self.overlay.listen_requested.connect(self.toggle_start)
                self.overlay.console_requested.connect(self.toggle_console)
                self.overlay.close_requested.connect(self._on_overlay_close)
            return self.overlay

        def enter_overlay_mode(self, start_listening: bool = False) -> None:
            """与 LocalLiveCaption 一致：默认只显示字幕，主窗口留在内存负责后台流水线。"""
            app = QtWidgets.QApplication.instance()
            if app is not None:
                app.setQuitOnLastWindowClosed(False)
            self._overlay_only = True
            self._overlay_is_primary = True
            self.btn_close.setToolTip("隐藏主界面，保留悬浮字幕与识别")
            # 禁止继承旧配置中不可点击的状态，否则第一次启动无法打开设置或退出。
            if self.cfg.get("overlay.click_through", False):
                self.cfg.set("overlay.click_through", False, save=False)
            if not self.btn_overlay.isChecked():
                self.btn_overlay.setChecked(True)
            ov = self._ensure_overlay()
            ov.refresh()
            ov.show()
            ov.btn_close.setText("退出")
            ov.btn_console.setText("显示主界面")
            ov.btn_console.setToolTip("打开主界面（再次点击即可隐藏）")
            self._refresh_overlay()
            self._update_overlay_listen_button()
            self.btn_settings.setChecked(False)
            if self._settings_dialog is not None:
                self._settings_dialog.hide()
            self.hide()
            if not self._boot_done:
                self._boot_done = True
                QtCore.QTimer.singleShot(0, self._refresh_devices)
            if start_listening:
                QtCore.QTimer.singleShot(0, self._start_pipeline)

        def toggle_console(self) -> None:
            """悬浮字幕窗的「主界面」按钮：打开/隐藏同一个主界面，不重启音频流水线。"""
            if self.isVisible() and not self.isMinimized():
                self.enter_overlay_mode(start_listening=False)
            else:
                self.show_console()

        def show_console(self) -> None:
            """显示已有的主界面，不额外创建窗口或重新启动识别。"""
            self._overlay_only = False
            app = QtWidgets.QApplication.instance()
            if app is not None:
                # 字幕模式打开控制台后仍需保持后台字幕服务的独立生命周期。
                app.setQuitOnLastWindowClosed(not self._overlay_is_primary)
            self.btn_close.setToolTip(
                "隐藏主界面，保留字幕" if self._overlay_is_primary else "退出程序")
            if self.overlay is not None:
                self.overlay.btn_close.setText("隐藏")
                self.overlay.btn_console.setText("隐藏主界面")
                self.overlay.btn_console.setToolTip("关闭主界面，继续显示字幕和翻译")
            self.showNormal()
            self.raise_()
            self.activateWindow()

        def _on_overlay_close(self) -> None:
            if self._overlay_only:
                self.request_quit()  # 明确的「退出」才释放识别、翻译等资源
            else:
                self.btn_overlay.setChecked(False)

        def request_quit(self) -> None:
            """托盘与字幕条显式退出；区别于主窗口右上角的隐藏操作。"""
            self._quit_requested = True
            self.close()

        def _update_overlay_listen_button(self) -> None:
            if self.overlay is not None:
                running = self.pipeline is not None and self.pipeline.isRunning()
                self.overlay.btn_listen.setText("■ 停止" if running else "▶ 开始")

        def _toggle_overlay(self, on: bool) -> None:
            self.cfg.set("overlay.enabled", bool(on))
            ov = self._ensure_overlay()
            ov.refresh()
            ov.setVisible(bool(on))
            if on:
                self._refresh_overlay()
                if self._ui_ready:
                    self.toast_msg("悬浮字幕已开启：拖动移动，滚轮调字号，双击切换鼠标穿透；"
                                   "框的透明度在「设置 → 悬浮字幕窗」里调")

        def _refresh_overlay(self) -> None:
            if self.overlay is None or not self.overlay.isVisible():
                return
            items = [(s.jp, s.zh) for s in self.transcript.recent_segments(
                int(self.cfg.get("overlay.lines", 2)))]
            live_index = None
            if self._live_jp or self._live_zh:
                items.append((self._live_jp, self._live_zh))
                live_index = len(items) - 1
            if not items:
                items = [("", "等待语音…")]
            self.overlay.set_content(items, live_index)

        # ==================================================================
        def toggle_start(self) -> None:
            if self.pipeline is not None and self.pipeline.isRunning():
                self._stop_pipeline(drain=True)
            else:
                self._start_pipeline()

        def _start_pipeline(self) -> None:
            from ..core.pipeline import Pipeline

            if self._closing:
                return
            if self._retiring_pipelines:
                self._restart_requested = True
                self._on_status("正在释放上一轮模型…")
                return
            if self.pipeline is not None and self.pipeline.isRunning():
                return
            self.transcript.placeholder.setVisible(False)
            self.pipeline = Pipeline(self.cfg)
            self.pipeline.sig_status.connect(self._on_status)
            self.pipeline.sig_error.connect(self._on_error)
            self.pipeline.sig_partial.connect(self._on_partial)
            self.pipeline.sig_discontinuity.connect(self._on_audio_discontinuity)
            self.pipeline.sig_segment.connect(self._on_segment)
            self.pipeline.sig_live_zh.connect(self._on_live_zh)
            self.pipeline.sig_final_zh.connect(self._on_final_zh)
            self.pipeline.sig_level.connect(self.level.set_level)
            self.pipeline.sig_stats.connect(self._on_stats)
            self.pipeline.sig_translate_info.connect(self._on_translate_info)
            self.pipeline.finished.connect(self._pipeline_finished)
            self._session_start = time.time()
            self.pipeline.start()
            self.btn_start.setText("⏸  停止聆听")
            self._update_overlay_listen_button()
            self._on_status("正在启动…")

        def _stop_pipeline(self, *, drain: bool = False) -> None:
            self._restart_requested = False
            if self.pipeline is not None:
                old = self.pipeline
                disconnect = ("sig_status", "sig_partial", "sig_discontinuity", "sig_live_zh", "sig_level")
                if not drain:
                    disconnect += ("sig_error", "sig_segment", "sig_final_zh", "sig_stats", "sig_translate_info")
                # 只断开本窗口的连接，不误删其他观察者；已完成的字幕在排空期间继续投递。
                slots = {
                    "sig_status": self._on_status,
                    "sig_error": self._on_error,
                    "sig_partial": self._on_partial,
                    "sig_discontinuity": self._on_audio_discontinuity,
                    "sig_segment": self._on_segment,
                    "sig_live_zh": self._on_live_zh,
                    "sig_final_zh": self._on_final_zh,
                    "sig_level": self.level.set_level,
                    "sig_stats": self._on_stats,
                    "sig_translate_info": self._on_translate_info,
                }
                for name in disconnect:
                    try:
                        getattr(old, name).disconnect(slots[name])
                    except (RuntimeError, TypeError):
                        pass
                self._retiring_pipelines.append(old)
                old.stop(max_wait=0, graceful=drain)
                self.pipeline = None
            self.btn_start.setText("▶  开始聆听")
            self._update_overlay_listen_button()
            self._on_status("已停止")
            self.level.set_level(0.0)

        def _restart_if_running(self) -> None:
            if self.pipeline is None or not self.pipeline.isRunning():
                return
            self._stop_pipeline()
            self._restart_requested = True

        def _pipeline_finished(self) -> None:
            old = self.sender()
            if old in self._retiring_pipelines:
                self._retiring_pipelines.remove(old)
            if self.pipeline is old:
                self.pipeline = None
                self.btn_start.setText("▶  开始聆听")
            self._update_overlay_listen_button()
            if old.has_pending_tasks():
                # Do not delete a signal sender while native model work still
                # references its Python/Qt instance. The old generation is
                # rejected by UI callbacks after leaving _retiring_pipelines.
                self._orphaned_pipelines.append(old)
                self._orphan_timer.start()
            else:
                old.deleteLater()
            if self._restart_requested and not self._closing and not self._retiring_pipelines:
                self._restart_requested = False
                QtCore.QTimer.singleShot(0, self._start_pipeline)

        def _reap_orphaned(self) -> None:
            for old in tuple(self._orphaned_pipelines):
                if not old.has_pending_tasks():
                    self._orphaned_pipelines.remove(old)
                    old.deleteLater()
            if not self._orphaned_pipelines:
                self._orphan_timer.stop()

        def _allow_pipeline_signal(self) -> bool:
            # Direct UI calls (sender=None) remain valid. Only a stale
            # Pipeline QThread may be rejected; graceful tails are allowed.
            source = self.sender()
            return (not isinstance(source, QtCore.QThread)
                    or source is self.pipeline or source in self._retiring_pipelines)

        # ---- 管线事件 ------------------------------------------------------
        def _on_status(self, text: str) -> None:
            colors = {
                "正在启动…": "#ffd166", "正在聆听…": "#4fd08a", "已停止": "#9aa3b5",
                "启动失败": "#ff6b6b",
            }
            color = colors.get(text, "#7aa2ff")
            if "正在加载" in text or "正在打开" in text:
                color = "#ffd166"
            self.lbl_state.setText(f"● {text}")
            self.lbl_state.setStyleSheet(f"color: {color};")
            if "失败" in text or "出错" in text:
                self.toast_msg(text)
            elif "降级" in text or "不可用" in text:
                self.toast_msg(text + "（在 设置 → 翻译服务 里可换回或修复）")

        def _on_error(self, text: str) -> None:
            if not self._allow_pipeline_signal():
                return
            self.toast_msg(text)
            from ..paths import LOG_PATH
            try:
                with LOG_PATH.open('a', encoding='utf-8') as f:
                    f.write(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] {text}\n')
            except OSError:
                pass
            self.lbl_state.setToolTip(text)

        def _on_partial(self, text: str) -> None:
            self._live_jp = text
            if text:
                self.transcript.set_live_jp(text)
            self._refresh_overlay()

        def _on_audio_discontinuity(self) -> None:
            # 显式断流与普通 final 切句不同：丢弃无法校对的实时行，但保留已完成历史。
            self._live_jp = self._live_zh = ""
            self.transcript.clear_live()
            self._refresh_overlay()

        def _on_live_zh(self, sid: str, zh: str) -> None:
            if (self.pipeline is None or not self.pipeline._active
                    or self.pipeline._live['sid'] != sid):
                return
            self._live_zh = zh
            self.transcript.set_live_zh(zh)
            self._refresh_overlay()

        def _on_segment(self, seg: Segment) -> None:
            if not self._allow_pipeline_signal():
                return
            self.transcript.commit_segment(seg)
            self._live_jp = ""
            self._live_zh = ""
            self._refresh_overlay()

        def _on_final_zh(self, sid: str, zh: str) -> None:
            if not self._allow_pipeline_signal():
                return
            self.transcript.set_zh_for(sid, zh)
            self._refresh_overlay()

        def _on_stats(self, stats: dict) -> None:
            self.lbl_stats.setText(
                f"校对 {stats.get('asr_ms', 0)} ms · RTF {stats.get('rtf', 0)} · 语句 {stats.get('audio_s', 0)} s")

        def _on_translate_info(self, info: dict) -> None:
            if info.get('provider') == 'llamacpp':
                from ..core import llama_engine
                running = [s.variant.upper() for s in list(llama_engine._SERVERS.values())
                            if s.mmproj is None and s._proc is not None and s._proc.poll() is None]
                if running:
                    self.lbl_engine.setText('识别：日语专用 CPU · 翻译：' + running[-1])
            kind = "实时" if info.get("live") else "整句"
            self.lbl_trans.setText(
                f"翻译[{kind}]：{info.get('label', '')} {info.get('seconds', '')}s")

        def _update_trans_label_from_cfg(self) -> None:
            from ..core.config import TRANSLATE_PRESETS

            pid = str(self.cfg.get("translate.provider", ""))
            label = TRANSLATE_PRESETS.get(pid, {}).get("label", pid or "-")
            model = str(self.cfg.service(pid).get("model") or "")
            if pid == "llamacpp" and model:
                model = Path(model).name
            self.lbl_trans.setText(f"翻译：{label}" + (f" · {model}" if model else "") )

        # ---- 拖拽图片换背景 -------------------------------------------------
        _IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

        def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
            if e.mimeData().hasUrls():
                for u in e.mimeData().urls():
                    p = Path(u.toLocalFile())
                    if p.suffix.lower() in self._IMG_EXTS:
                        e.acceptProposedAction()
                        return
            e.ignore()

        def dropEvent(self, e: QtGui.QDropEvent) -> None:
            for u in e.mimeData().urls():
                p = Path(u.toLocalFile())
                if p.suffix.lower() in self._IMG_EXTS:
                    self.settings.add_background_file(p)
                    self.toast_msg(f"已设为背景照片：{p.name}（可在设置里调整模糊与暗度）")
                    e.acceptProposedAction()
                    return
            e.ignore()

        # ---- 设置联动 ------------------------------------------------------
        def _on_setting_changed(self, path: str, value) -> None:
            if path in ("ui.theme", "ui.accent", "ui.font"):
                self._apply_theme()
            elif path.startswith("ui.bg"):
                self._schedule_bg_apply()
            elif path in ("translate.provider", "translate.services", "translate.live_provider"):
                self._update_trans_label_from_cfg()
            elif path.startswith("translate.services.llamacpp"):
                # 清理旧引擎必须异步，否则模型启动/退出时持有锁会冻结 Qt 主线程。
                # 只切换运行变体时保留可能已由新翻译请求启动的目标引擎。
                keep_variant = None
                if path == "translate.services.llamacpp.variant":
                    requested = str(self.cfg.get(path, "auto"))
                    if requested in ("cpu", "vulkan", "cuda"):
                        keep_variant = requested
                    else:
                        from ..core.llama_engine import preferred_variant
                        keep_variant = preferred_variant(self.cfg)
                self._engine_stop_scheduler.request(keep_variant)
                self._update_trans_label_from_cfg()
            elif path in ("ui.jp_size", "ui.zh_size", "ui.display", "ui.history_limit"):
                self.transcript.set_sizes(int(self.cfg.get("ui.jp_size", 13)), int(self.cfg.get("ui.zh_size", 19)))
                self.transcript.set_display_mode(str(self.cfg.get("ui.display", "both")))
                if path == "ui.history_limit":
                    self.transcript.set_max_lines()
                    if self.pipeline is not None:
                        keep = max(1, min(1000, int(self.cfg.get("ui.history_limit", 3))))
                        self.pipeline._last_final_jp = self.pipeline._last_final_jp[-keep:]
                        self.pipeline.trim_pending_translations()
                    self._refresh_overlay()
            elif path == "overlay.enabled":
                on = bool(self.cfg.get("overlay.enabled", False))
                if self.btn_overlay.isChecked() != on:
                    self.btn_overlay.setChecked(on)
                self._toggle_overlay(on)
            elif path.startswith("overlay."):
                if self.overlay is not None:
                    self.overlay.refresh()
                    self.overlay.setVisible(bool(self.cfg.get("overlay.enabled", False)))
            elif path in ("audio.source",):
                self._refresh_devices()
                self._restart_if_running()
            elif path in ("audio.device", "asr.partial", "asr.draft_mode", "asr.final_engine", "vad.threshold",
                          "vad.min_silence_ms", "asr.max_segment_s", "asr.context_prompt",
                          "asr.cloud.base_url", "asr.cloud.model", "asr.cloud.api_key", "asr.cloud.preset"):
                if self.pipeline is not None and self.pipeline.isRunning():
                    self._restart_if_running()
                    self.toast_msg("设置已应用，识别已自动重启")

        # ==================================================================
        def _clear(self) -> None:
            self.transcript.clear_all()
            self._live_jp = self._live_zh = ""
            self._refresh_overlay()

        def _show_history(self) -> None:
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("本次会话 · 当前保留的字幕")
            dialog.resize(760, 620)
            layout = QtWidgets.QVBoxLayout(dialog)
            header = QtWidgets.QLabel("仅显示设置中允许保留的最近字幕；更早的原文和译文已从内存删除。")
            header.setWordWrap(True)
            layout.addWidget(header)
            search_row = QtWidgets.QHBoxLayout()
            query = QtWidgets.QLineEdit()
            query.setPlaceholderText("查找原文或译文")
            find_button = QtWidgets.QPushButton("查找下一个")
            refresh_button = QtWidgets.QPushButton("刷新记录")
            search_row.addWidget(query, 1)
            search_row.addWidget(find_button)
            search_row.addWidget(refresh_button)
            layout.addLayout(search_row)
            text = QtWidgets.QPlainTextEdit()
            text.setReadOnly(True)
            layout.addWidget(text, 1)

            def refresh() -> None:
                parts = []
                for s in self.transcript.all_segments():
                    stamp = f"{int(s.t0 // 60):02d}:{int(s.t0 % 60):02d}"
                    parts.append(f"[{stamp}] {s.jp}\n{s.zh}".rstrip())
                text.setPlainText("\n\n".join(parts) if parts else "本次会话还没有字幕记录。")

            def find_next() -> None:
                needle = query.text().strip()
                if needle and not text.find(needle):
                    cursor = text.textCursor()
                    cursor.movePosition(QtGui.QTextCursor.MoveOperation.Start)
                    text.setTextCursor(cursor)
                    text.find(needle)

            find_button.clicked.connect(find_next)
            query.returnPressed.connect(find_next)
            refresh_button.clicked.connect(refresh)
            refresh()
            dialog.exec()

        def _export(self) -> None:
            segs = self.transcript.all_segments()
            if not segs:
                self.toast_msg("还没有可导出的字幕")
                return
            default = HISTORY / f"字幕_{time.strftime('%Y%m%d_%H%M%S')}.srt"
            path, _f = QtWidgets.QFileDialog.getSaveFileName(
                self, "导出字幕", str(default), "SRT 字幕 (*.srt);;纯文本 (*.txt)")
            if not path:
                return
            try:
                if path.lower().endswith(".txt"):
                    lines = []
                    for s in segs:
                        lines.append(s.jp)
                        if s.zh:
                            lines.append(s.zh)
                        lines.append("")
                    Path(path).write_text("\n".join(lines), encoding="utf-8")
                else:
                    Path(path).write_text(self._to_srt(segs), encoding="utf-8")
                self.toast_msg(f"已导出：{path}")
            except Exception as e:  # noqa: BLE001
                self.toast_msg(f"导出失败：{e}")

        def _to_srt(self, segs: list[Segment]) -> str:
            def fmt(t: float) -> str:
                h = int(t // 3600)
                m = int(t % 3600 // 60)
                s = int(t % 60)
                ms = int((t - int(t)) * 1000)
                return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

            out = []
            for i, seg in enumerate(segs, 1):
                out.append(str(i))
                out.append(f"{fmt(seg.t0)} --> {fmt(max(seg.t1, seg.t0 + 0.5))}")
                if seg.zh:
                    out.append(seg.zh)
                out.append(seg.jp)
                out.append("")
            return "\n".join(out)

        # ==================================================================
        def toast_msg(self, text: str, msec: int = 4200) -> None:
            self.toast.setText(text)
            self.toast.adjustSize()
            self._place_toast()
            self.toast.show()
            self.toast.raise_()
            self._toast_timer.start(msec)

        def _place_toast(self) -> None:
            x = (self.width() - self.toast.width()) // 2
            self.toast.move(max(10, x), self.titlebar.height() + 8)

        # ---- 托盘 ----------------------------------------------------------
        def _build_tray(self) -> None:
            if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
                self.tray = None
                return
            icon_path = ASSETS / "icon.png"
            icon = QtGui.QIcon(str(icon_path)) if icon_path.exists() else self.style().standardIcon(
                QtWidgets.QStyle.StandardPixmap.SP_MediaPlay)
            self.tray = QtWidgets.QSystemTrayIcon(icon, self)
            menu = QtWidgets.QMenu()
            act_show = menu.addAction("显示主窗口")
            act_show.triggered.connect(self.show_console)
            act_overlay_only = menu.addAction("仅显示字幕条")
            act_overlay_only.triggered.connect(self.enter_overlay_mode)
            act_toggle = menu.addAction("开始 / 停止聆听")
            act_toggle.triggered.connect(self.toggle_start)
            act_ov = menu.addAction("显示/隐藏悬浮字幕")
            act_ov.triggered.connect(lambda: self.btn_overlay.toggle())
            menu.addSeparator()
            act_quit = menu.addAction("退出程序（停止识别和翻译）")
            act_quit.triggered.connect(self.request_quit)
            self.tray.setContextMenu(menu)
            self.tray.setToolTip(APP_NAME)
            self.tray.activated.connect(
                lambda r: self.show_console()
                if r == QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick else None)
            self.tray.show()

        # ---- 快捷键 --------------------------------------------------------
        def _install_shortcuts(self) -> None:
            QtGui.QShortcut(QtGui.QKeySequence("F9"), self, activated=self.toggle_start)
            QtGui.QShortcut(QtGui.QKeySequence("F10"), self, activated=lambda: self.btn_overlay.toggle())
            QtGui.QShortcut(QtGui.QKeySequence("Esc"), self, activated=lambda: self.btn_settings.setChecked(False))

        # ---- 窗口移动/缩放 --------------------------------------------------
        _EDGE = 8

        def _edge_at(self, pos: QtCore.QPoint) -> str:
            edges = []
            if pos.x() < self._EDGE:
                edges.append("l")
            if pos.x() > self.width() - self._EDGE:
                edges.append("r")
            if pos.y() < self._EDGE:
                edges.append("t")
            if pos.y() > self.height() - self._EDGE:
                edges.append("b")
            return "".join(edges)

        def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
            if e.button() != QtCore.Qt.MouseButton.LeftButton:
                return
            pos = e.position().toPoint()
            edge = self._edge_at(pos)
            if edge:
                self._resize_edges = edge
                self._resize_start = (e.globalPosition().toPoint(), self.geometry())
                e.accept()
                return
            # 标题栏空白处按下 = 拖动整个窗口（无边框窗口得自己实现，否则只能拉边缘改大小）
            if self.titlebar.geometry().contains(pos):
                self._start_move(e.globalPosition().toPoint())
                e.accept()

        def _start_move(self, global_pos: QtCore.QPoint) -> None:
            """开始拖动窗口：优先交给系统（有吸附、跨屏更顺），不行就自己算坐标移动。"""
            handle = self.windowHandle()
            if handle is not None:
                try:
                    if handle.startSystemMove():
                        return
                except Exception:  # noqa: BLE001
                    pass
            self._drag_pos = global_pos - self.frameGeometry().topLeft()

        def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
            pos = e.position().toPoint()
            if self._drag_pos is not None:                 # 拖动窗口
                self.move(e.globalPosition().toPoint() - self._drag_pos)
                e.accept()
                return
            if self._resize_start and self._resize_edges:
                gp, geo = self._resize_start
                d = e.globalPosition().toPoint() - gp
                new = QtCore.QRect(geo)
                if "l" in self._resize_edges:
                    new.setLeft(min(geo.left() + d.x(), geo.right() - self.minimumWidth()))
                if "r" in self._resize_edges:
                    new.setRight(max(geo.right() + d.x(), geo.left() + self.minimumWidth()))
                if "t" in self._resize_edges:
                    new.setTop(min(geo.top() + d.y(), geo.bottom() - self.minimumHeight()))
                if "b" in self._resize_edges:
                    new.setBottom(max(geo.bottom() + d.y(), geo.top() + self.minimumHeight()))
                self.setGeometry(new)
                e.accept()
                return
            edge = self._edge_at(pos)
            cursors = {
                "l": QtCore.Qt.CursorShape.SizeHorCursor, "r": QtCore.Qt.CursorShape.SizeHorCursor,
                "t": QtCore.Qt.CursorShape.SizeVerCursor, "b": QtCore.Qt.CursorShape.SizeVerCursor,
                "lt": QtCore.Qt.CursorShape.SizeFDiagCursor, "rb": QtCore.Qt.CursorShape.SizeFDiagCursor,
                "rt": QtCore.Qt.CursorShape.SizeBDiagCursor, "lb": QtCore.Qt.CursorShape.SizeBDiagCursor,
            }
            self.setCursor(cursors.get(edge, QtCore.Qt.CursorShape.ArrowCursor))

        def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
            if self._drag_pos is not None:
                self._drag_pos = None
                self._save_geometry()
                e.accept()
                return
            if self._resize_start:
                self._resize_start = None
                self._resize_edges = ""
                self._save_geometry()

        def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
            self.bg.setGeometry(self.rect())
            QtCore.QTimer.singleShot(180, self._reflow_bg)
            btn = getattr(self, "btn_settings", None)
            anim = getattr(self, "_drawer_anim", None)
            anim_running = False
            if anim is not None:
                try:
                    anim_running = anim.state() == QtCore.QAbstractAnimation.State.Running
                except RuntimeError:
                    anim_running = False  # C++ 对象已析构，当作不在运行
            if btn is not None and btn.isChecked() and not anim_running:
                # 窗口变窄时重新算一次抽屉宽度，尽量不让设置内容被裁掉
                self._set_drawer_width(self.drawer_width())
            super().resizeEvent(e)

        def _reflow_bg(self) -> None:
            if self.isVisible():
                self.bg.reflow()

        def moveEvent(self, e: QtGui.QMoveEvent) -> None:
            self._save_geometry_debounced()
            super().moveEvent(e)

        def _save_geometry_debounced(self) -> None:
            if self._closing:
                return  # 退出后不再创建新的写盘回调。
            if not hasattr(self, "_geo_timer"):
                self._geo_timer = QtCore.QTimer(self)
                self._geo_timer.setSingleShot(True)
                self._geo_timer.timeout.connect(self._save_geometry)
            self._geo_timer.start(600)

        def _save_geometry(self) -> None:
            if self.cfg.load_error:
                return  # Invalid user JSON is never replaced by window geometry.
            self.cfg.update_many({
                "ui.window.w": self.width(), "ui.window.h": self.height(),
                "ui.window.x": self.x(), "ui.window.y": self.y(),
            })

        def closeEvent(self, e: QtGui.QCloseEvent) -> None:
            # 由字幕模式打开的控制台只是辅助界面；用户点 X/Alt+F4 时仅隐藏。
            # 不触发 _stop_pipeline、stop_all 或 app.quit，确保字幕连续运行。
            if self._overlay_is_primary and not self._quit_requested and self.isVisible():
                e.ignore()
                self.enter_overlay_mode(start_listening=False)
                return
            self._closing = True          # 仅显式退出（或传统主窗口模式）需要释放资源
            if hasattr(self, "_geo_timer"):
                self._geo_timer.stop()     # 退出前取消旧版可能延迟写回的窗口尺寸
            if self.pipeline is not None:
                self._stop_pipeline()
            if self._retiring_pipelines:
                self._on_status("正在退出，等待模型完成当前任务…")
                QtCore.QTimer.singleShot(200, self.close)
                e.ignore()
                return
            if self._quit_cleanup_thread is None:
                # Close the visible surfaces at once; GPU cleanup must never
                # hold the Qt event thread while waiting on llama-server/_LOCK.
                self._save_geometry()
                self.hide()
                if self.overlay is not None:
                    self.overlay.hide()
                if self.tray is not None:
                    self.tray.hide()
                if self._settings_dialog is not None:
                    self._settings_dialog.hide()
                self._on_status("正在后台关闭翻译引擎…")

                def shutdown_engine() -> None:
                    try:
                        # Serialize with any outstanding engine-switch worker.
                        self._engine_stop_scheduler.wait(20.0)
                        from ..core.llama_engine import stop_all
                        stop_all()
                    except Exception as exc:  # noqa: BLE001
                        self._quit_cleanup_error = str(exc)
                    finally:
                        self._quit_cleanup_done.set()

                # Non-daemon: process lifetime must not silently truncate a
                # partially completed engine teardown.
                self._quit_cleanup_thread = threading.Thread(
                    target=shutdown_engine, name="YishengTranslator-shutdown", daemon=False)
                self._quit_cleanup_thread.start()
                self._quit_poll = QtCore.QTimer(self)
                self._quit_poll.timeout.connect(
                    lambda: self.close() if self._quit_cleanup_done.is_set() else None)
                self._quit_poll.start(40)
                e.ignore()
                return
            if not self._quit_cleanup_done.is_set():
                e.ignore()
                return
            if self._quit_poll is not None:
                self._quit_poll.stop()
            if self._quit_cleanup_error:
                self._on_error(f"关闭翻译引擎时出现错误：{self._quit_cleanup_error}")
            if self._settings_dialog is not None:
                self._settings_dialog.close()
            if self.overlay is not None:
                self.overlay.close()
            if self._config_warning is not None:
                self._config_warning.close()
            e.accept()
            # Subtitle-only mode disables quitOnLastWindowClosed.
            app = QtWidgets.QApplication.instance()
            if app is not None:
                QtCore.QTimer.singleShot(0, app.quit)
# END MODULE: jpsub.ui.window