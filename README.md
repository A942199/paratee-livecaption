# YishengTranslator（译声实时翻译）

Windows x64 日语语音识别与中文字幕工具。本开发分支提供个人使用的首次启动依赖检查，尚未合并到 main。

## 在另一台已有 Python 的 Windows 电脑上使用

1. Windows 10/11 x64，已安装 Python 3.11 或 3.12 x64，并可用 pythonw.exe 双击运行 .pyw。
2. 把主程序 YishengTranslator_memory_limit.pyw、yisheng_startup.py、requirements.txt 放到同一目录。
3. 同时复制原电脑的 models/、engine/、jpsub/assets/。这三类模型/引擎/界面资源**不包含在 GitHub 仓库中**；只复制 .pyw 不够。
4. 双击 YishengTranslator_memory_limit.pyw。若本机 Python 依赖齐全则直接运行；否则会在 %LOCALAPPDATA%/YishengTranslator/envs/ 中创建专用虚拟环境，并自动安装缺失依赖后启动。
5. 如提示资源缺失，从原电脑复制；大型模型不会自动下载。也可以使用原程序设置中的模型下载选项。

首次 pip 安装需联网；失败详情记录于 %LOCALAPPDATA%/YishengTranslator/envs/bootstrap.log。不修改系统 Python，不建议跨电脑复制 .venv。可选复制私人 config.json，但不要公开上传。

## 验证（开发使用）

```powershell
python -m unittest discover -s tests -p test_*.py -v
python -m py_compile YishengTranslator_memory_limit.pyw yisheng_startup.py
python YishengTranslator_memory_limit.pyw --bundle-check
python YishengTranslator_memory_limit.pyw --selftest
```

bundle-check 需要完整的 12 份界面资源；selftest 需要 Parakeet 与 Silero VAD 模型。这些检查不能替代在新电脑上的真实音频/GPU 验证。

## 最小修改原则

仅在现有 .pyw 的 _main() 入口调用 yisheng_startup.prepare()，不修改 ASR、翻译或字幕的业务代码。
