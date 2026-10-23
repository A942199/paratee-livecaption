"""Regression tests for first-run setup. No downloads or system changes."""
from __future__ import annotations
from pathlib import Path
import os
import tempfile
import unittest
from unittest import mock
import yisheng_startup as mod

class StartupTests(unittest.TestCase):
    def test_versions(self):
        self.assertTrue(mod._compare_version("6.7.2", ">=", "6.7"))
        self.assertTrue(mod._compare_version("1.26", "<", "3"))
        self.assertFalse(mod._compare_version("7", "<", "7"))
        self.assertFalse(mod._compare_version("1.9", ">=", "2"))
        self.assertFalse(mod._compare_version("bad", "==", "1"))

    def test_requirements(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "requirements.txt"
            p.write_text("PySide6>=6.7,<7\nnumpy>=1.26,<3\n")
            self.assertEqual(len(mod._requirements(p)), 2)
            p.write_text("numpy>=notaversion\n")
            with self.assertRaises(mod.SetupError):
                mod._requirements(p)

    def test_missing_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(mod.SetupError):
                mod._requirements(Path(d) / "requirements.txt")

    def test_installed_versions(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "requirements.txt"
            p.write_text("numpy>=1.26,<3\n")
            with mock.patch.object(mod.importlib.metadata,"version",return_value="1.24"):
                self.assertFalse(mod._dependencies_ok(p))
            with mock.patch.object(mod.importlib.metadata,"version",return_value="1.26.4"):
                self.assertTrue(mod._dependencies_ok(p))

    def test_resources(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            self.assertEqual(len(mod._resource_warnings(root)), 6)
            for path in ("jpsub/assets/icon.png", "models/parakeet-ja-0.6b-int8/model.int8.onnx",
                         "models/parakeet-ja-0.6b-int8/tokens.txt", "models/silero_vad.onnx",
                         "models/llm/Hy-MT2-7B-Q4_K_M.gguf", "engine/cpu/llama-server.exe"):
                f=root/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b"x")
            self.assertEqual(mod._resource_warnings(root),[])

    def test_child_skips_bootstrap(self):
        with mock.patch.dict(os.environ,{mod.ENV_CHILD:"1"}),mock.patch.object(mod,"_prepare_environment") as factory:
            self.assertFalse(mod.prepare(Path.cwd(),Path("a.pyw"),[]))
            factory.assert_not_called()

    def test_no_launch_if_python_ready(self):
        with tempfile.TemporaryDirectory() as d,\
             mock.patch.object(mod.sys,"platform","win32"),\
             mock.patch.object(mod.sys,"maxsize",2**63-1),\
             mock.patch.object(mod,"_prepare_environment",return_value=None),\
             mock.patch.object(mod,"_resource_warnings",return_value=[]),\
             mock.patch.object(mod.subprocess,"Popen") as proc:
            root=Path(d);main=root/"YishengTranslator_memory_limit.pyw";main.write_text("test")
            self.assertFalse(mod.prepare(root,main,[]))
            proc.assert_not_called()

    def test_spawn_venv_exactly_once(self):
        with tempfile.TemporaryDirectory() as d,\
             mock.patch.object(mod.sys,"platform","win32"),\
             mock.patch.object(mod.sys,"maxsize",2**63-1),\
             mock.patch.object(mod,"_prepare_environment",return_value=Path("pythonw.exe")),\
             mock.patch.object(mod,"_resource_warnings",return_value=[]),\
             mock.patch.object(mod.subprocess,"Popen") as proc:
            root=Path(d);main=root/"YishengTranslator_memory_limit.pyw";main.write_text("test")
            self.assertTrue(mod.prepare(root,main,["--main-window"]))
            args,kwargs=proc.call_args
            self.assertEqual(args[0][-1],"--main-window")
            self.assertEqual(kwargs["env"][mod.ENV_CHILD],"1")
            self.assertEqual(kwargs["env"][mod.DELEGATED],"1")

    def test_failure_does_not_launch(self):
        with tempfile.TemporaryDirectory() as d,\
             mock.patch.object(mod.sys,"platform","win32"),\
             mock.patch.object(mod.sys,"maxsize",2**63-1),\
             mock.patch.object(mod,"_prepare_environment",side_effect=mod.SetupError("pip failed")) ,\
             mock.patch.object(mod,"_notify"),\
             mock.patch.object(mod.subprocess,"Popen") as proc:
            root=Path(d);main=root/"YishengTranslator_memory_limit.pyw";main.write_text("test")
            with self.assertRaises(mod.SetupError):mod.prepare(root,main,[])
            proc.assert_not_called()

    def test_cached_environment_probe(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(mod.subprocess, "run") as run:
            python = Path(d) / "python.exe"
            python.write_bytes(b"fake")
            run.return_value.returncode = 0
            self.assertTrue(mod._environment_ok(python, Path(d) / "requirements.txt", Path(d)))
            run.return_value.returncode = 1
            self.assertFalse(mod._environment_ok(python, Path(d) / "requirements.txt", Path(d)))
            run.side_effect = OSError("interpreter removed")
            self.assertFalse(mod._environment_ok(python, Path(d) / "requirements.txt", Path(d)))

    def test_existing_project_venv_is_reused(self):
        """A working local .venv must bypass pip even when the launcher lacks deps."""
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            python=root/".venv/Scripts/python.exe"
            pythonw=root/".venv/Scripts/pythonw.exe"
            python.parent.mkdir(parents=True)
            python.write_bytes(b"python")
            pythonw.write_bytes(b"pythonw")
            (root/"requirements.txt").write_text("numpy>=1.26,<3\n")
            with (mock.patch.object(mod,"_dependencies_ok",return_value=False),
                  mock.patch.object(mod,"_environment_ok",return_value=True) as probe,
                  mock.patch.object(mod,"_run_command",side_effect=AssertionError("must not install"))):
                self.assertEqual(mod._prepare_environment(root),pythonw)
                probe.assert_called_once_with(python,root/"requirements.txt",root)

    def test_failed_command_preserves_exit(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(mod.subprocess,"run") as run:
            run.return_value.returncode=12
            with self.assertRaisesRegex(mod.SetupError,"12"):
                mod._run_command(["python","-m","pip"],Path(d)/"bootstrap.log",10)
            self.assertTrue((Path(d)/"bootstrap.log").is_file())

if __name__=="__main__":
    unittest.main()
