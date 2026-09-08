# 本地流式语音输入（当前源码）

> 2026-09-09：**流式预览 + 本地 Qwen3-ASR 0.6B 停句校准已接入正式面试页面。** 前期依据保留在[单模型对照](local-stt-comparison.zh.md)与[双阶段组合验证](local-stt-two-pass-validation.zh.md)；下面单独记录正式应用验证，不混用实验成绩。

模拟面试默认使用 **Zipformer 实时预览 + Silero 人声停顿检测 + Qwen3-ASR 0.6B int8 本地校准**。录音期间即可看到文字；每次停顿约 0.8 秒后，后台根据该段原音频校准预览，下一段可以继续说。SenseVoice 保持移除，没有隐藏回退。

不需要 API Key、PyTorch、服务器或新增桌面依赖。语音在 CPU 上本地识别，文字面试官仍可使用 DeepSeek、Codex 等；本次只更新源码，不代表旧 Windows/macOS 下载包已更新。

## 使用

1. 在回答框点击「语音输入」。上方显示实时预览，停句后自动校准；可以同时手打，不覆盖已有草稿，不用逐句点击转录。
2. 说完点击「完成录音」。最后一段及已排队的校准完成后，把本次结果一次性追加到回答框，不重复追加临时结果。
3. 检查、修改，再点击「提交并继续」。识别不会自动提交、评分或生成下一问。

首次未安装时，在「语音设置」点击「下载本地模型」，完整组合约 **1,188 MB（1.19 GB）**。已有 199 MB 流式模型时只补齐约 **989 MB** 校准资产，支持进度、取消和重试，已校验文件复用。首次停句会加载 Qwen，预览不等待它；后续复用已加载模型，每次使用独立识别状态。仅装旧预览模型不再标记为完整组合已就绪。

录音、停止和模型加载不占用面试的全局 busy 状态。录音或校准期间不允许提交半成品，但可继续编辑草稿。校准失败显示具体原因，不把预览悄悄当成校准成功；原草稿、WAV 保留，可点击「重试转成文字」，使用同一套双阶段管线。不会改用 SenseVoice 或自动上传。

## 数据、授权与迁移

模型保存于当前应用数据根目录的：

```text
models/stt/zipformer-bilingual-streaming-int8/
```

按[源码运行说明](desktop-app.md#源码运行)启动时，本机已经下载并逐文件验证：

```text
workspace/maintainer/manual-uat/models/stt/zipformer-bilingual-streaming-int8/
```

关闭旧源码进程，再按原命令启动即可使用，不需重新创建 Profile。换成其他数据根目录时需在对应目录下载模型。旧版本保存的本地转录选项恢复为新的本地流式选项，不会意外切到远程服务。

旧的 SenseVoice 模型缓存没有擅自删除，但当前代码不读取、不加载它。Profile、简历、回答和既有录音没有迁移或清空；模型、录音和截图均不进入源代码提交。

- 本地识别只访问当前授权操作的 PCM / WAV，不读取其他 Profile、材料或 API Key。
- 离开面试页会停止采音；同题已开始的识别可完成并回到原草稿，不抢其他页面焦点。
- 暂停、结束、到时、切换 Profile / 问题或关闭时，取消流式结果写回。WAV 保留，恢复后可显式重试。
- 可选远程 STT 仍是停录后上传，必须每次明确授权；本地失败不会自动切换远程。
- **音频不上传不等于回答不发送**：随后主动提交的回答文字属于本场面试已确认的 AI 发送范围。

## 模型来源与许可

采用 [sherpa-onnx 官方 Streaming Zipformer 模型](https://k2-fsa.github.io/sherpa/onnx/pretrained_models/online-transducer/zipformer-transducer-models.html#csukuangfj-sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20-bilingual-chinese-english)，模型仓库为 [csukuangfj/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20](https://huggingface.co/csukuangfj/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20)。

固定修订：`98590b7ed6443e77b714204da2757d75e1a642f4`。模型卡明确声明 [Apache-2.0](https://huggingface.co/csukuangfj/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20/blob/98590b7ed6443e77b714204da2757d75e1a642f4/README.md)，模型卡也随权重保存。不是用引擎的许可推断权重许可。

`ai/local_transcription.py` 固定 encoder int8、decoder fp32、joiner int8、tokens 和模型卡的大小及 SHA-256。运行前校验，模型目录不含原始训练检查点。本次维护者下载因网络限制使用公开 HF 镜像，文件 SHA 与上游固定修订一致；应用下载默认仍指向原始 Hugging Face 来源。

## 实现边界

校准采用 [Qwen3-ASR 0.6B 官方模型](https://huggingface.co/Qwen/Qwen3-ASR-0.6B)（模型卡声明 Apache-2.0），通过 [sherpa-onnx 的 Qwen3-ASR 接口](https://k2-fsa.github.io/sherpa/onnx/qwen3-asr/index.html) 在 CPU 推理。本轮复用已验证的 [ONNX 转换权重](https://modelscope.cn/models/zengshuishui/Qwen3-ASR-onnx)：encoder / frontend / tokenizer 修订 `c69fb1666ccb59a82c09840c511a6c894e6a2482`，int8 decoder 修订 `de9e449eb376dcb472c1ce8141fbae8d524fabbd`。第三方 ONNX 转换不冒充 Qwen 官方原始权重发布。

人声检测使用 [Silero v5.1.2](https://github.com/snakers4/silero-vad/tree/v5.1.2)，[MIT 许可](https://github.com/snakers4/silero-vad/blob/v5.1.2/LICENSE)。`ai/local_stt_assets.py` 固定校准权重、tokenizer、VAD 及许可证的来源、大小、SHA-256；14 个文件已在本机当前模型目录全部校验。未新增云端请求、PyTorch/vLLM 依赖或 1.7B 模型选项。

单个 Qt `QAudioSource` 收音，PCM 同时写入 Profile 内 WAV 和后台队列。实际采集帧数决定时长，不用虚假墙钟。Qt 主线程每 80 ms 取音，不执行模型加载或推理；采集停止不等待 ASR。

后台 `OnlineRecognizer` 生成预览，独立 Silero VAD 决定音频边界：最短人声 0.25 秒、静音 0.8 秒、连续语段上限 30 秒。不能用“预览没字”判断没有声音。原音频段交给单个后台校准工作线程，通过段 ID 替换预览，不把两份结果叠加。

Zipformer 与 Qwen 各用 CPU 2 线程，VAD 1 线程。校准模型验证和首次加载也在校准线程执行，不拦住预览。长静音只保留起音前缓冲；44.1 / 48 kHz 设备使用已有 SciPy 做带连续滤波上下文的重采样，不新增依赖。

结束时补齐预览右侧上下文，VAD flush 尾句，不重新识别整场录音。实时结果仍受 Profile、Interview、Question、Operation ID 校验，只有最终文字追加到草稿。取消跳过未开始的校准；原生推理中的调用可能稍后结束，但结果被丢弃，不等待它才允许下一次录音预览。

当前 PySide 的旧 `QAudio` 枚举与实际返回的 `QtAudio` 枚举不相等；源码使用 `QtAudio`，并在现有收音节拍中检查设备状态，避免旧 signal 签名转换错误。没有增加新的录音框架或服务。

## 正式双阶段应用验证（2026-09-09）

- `test_local_transcription.py`、`test_two_pass_transcription.py`、`test_voice.py`：**25 passed**。含真实模型、静音、无停顿尾句、48 kHz 双声道六段音频、按段替换、取消后立即重启、排队取消、44.1 / 48 kHz 重采样、嵌套下载与旧文件复用。
- `test_interview_input_runtime.py -k "real_local_stt_from_production_page or dictation or streaming or local_stt"`：最终 **19 个对应案例通过**（首次 18 passed / 1 failed；改善加载顺序与测试的 Qt 事件循环等待后，两项真实模型案例单独重验 **2 passed**）。不是全文件测试。
- `test_interview_input_runtime.py -k real_two_pass_corrects_pauses`：**1 passed**。正式 Windows QML、隔离合成档案、公开/TTS 音频按录音节拍回放、真实模型；停录前已自动校准两段，校准期间中文输入法提交的文字保留，预览继续变化 11 次，结果只追加一次，未自动提交回答。
- 收尾补充“暂时没有新 PCM 时也要发布停句校准结果”，运行上述管线测试、四种尺寸录音交互和双段真实模型 QML：**15 passed / 90 deselected**。包含新补的空输入唤醒测试，没有新增假音频或伪造录音计时。
- 最后一次双段样例首次校准（含加载）**7.57 秒**，下一段 **2.62 秒**；全部语段已校准后点击完成到观察完成 **0.27 秒**，不是任意尾句延迟。校准期间预览变化 13 次，Qt 20 ms 心跳最大间隔 **113 ms**。前次相同样例首次 / 后续为 6.55 / 2.74 秒，说明本机耗时也会波动。
- 公开约 5.59 秒中文样例：900×620 / 125% 与 1280×800 页面等待首段文字约 **2.89 / 2.83 秒**；立即停录后的首次校准约 **5.87 / 6.49 秒**。纯推理验证中，39.55 秒六段样例约 **9.91 秒**，六段均保留。

正式截图保存在 ignored 的 `workspace/maintainer/two-pass-production-20260908/screenshots/`（目录名为跨午夜工作开始日期）。已查看小窗口最终回答和双段预览、最终回答截图；其他录音布局定向案例覆盖四种窗口尺寸及深浅主题。

真实推理阻止 Python 网络连接与密钥读取；这不是操作系统网络沙箱。没有读取或识别私人环境音、真实简历或旧录音；本轮未重新测试实际麦克风，录音器未修改。

**准确率限制**：本轮仍有“验证集”识别为“验证及”，以及 `GRPO` 写成 `G R P O`。另一样例输出繁体字与阿拉伯数字。这些结果未用关键词替换掩盖，仍需人工编辑。测试接受简繁/数字等价写法，不能证明术语无误。未执行 macOS 实机、长时间无停顿语音准确率基准、云端 STT、全量 pytest、CI 或桌面打包。

## 历史单阶段验证（2026-09-08，非当前双阶段速度）

- 真实模型：公开中文音频约 5.59 秒，累计输入 **1.70 秒音频**时已有文字，停录前产生 7 次文本更新。首次加载与识别约 **1.12 秒**；39.55 秒、六段、48 kHz 双声道样例约 **2.10 秒**，六次「早上九点 / 下午五点」全部保留。推理期间禁止网络。
- 正式 QML 页面逐帧回放同一公开音频：900×620 / 125% 字体与 1280×800 下，测试从开始等待到出现「早上」约 **2.90 / 2.84 秒**；停录后的尾句处理约 **0.54 / 0.49 秒**，保留原草稿、没有自动提交。
- 真正 Windows 麦克风：连续三次录音 **3.68 / 3.70 / 3.70 秒**，停止响应 **66 / 59 / 60 毫秒**；每次均有实时 PCM、计时增长、有效 16 kHz 单声道 WAV，之前 WAV 哈希不变。此项用识别替身，**没有识别或上传私人环境声音**；实际识别由上一项公开音频单独证明。
- 正式页面定向操作覆盖 900×620、1080×680、1280×800、1440×900，含深浅主题及 125% 字体，已查看代表截图。验证停录期间仍可键入、最终文本不重复、失效上下文不回写、原录音可重试，以及移除旧模型后的选项恢复。
- 实现中的原生测试曾发现 `QAudio` / `QtAudio` 不兼容导致错误拒绝麦克风；已修复，并重新通过三次原生录停。

证据保存在 ignored 的 `workspace/maintainer/streaming-stt-validation/screenshots/`，使用合成测试档案的正式页面，而非 demo 页面或真实简历。

这些是样例/本机耗时，不是准确率基准或所有设备的速度保证。专有名词、口音、噪声、标点和数字格式仍可能需要修改；当前样例输出中文数字，未加入额外标点/ITN 模型。没有进行 macOS 实机、真实远程 STT、全量 pytest、CI 或桌面打包。

### 可复验的目标命令

默认测试不下载模型，不读取私人录音，不打开麦克风。真实模型需显式指定公开音频：

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) "src"
$env:LLM_LAB_TEST_LOCAL_STT_MODEL_ROOT = Join-Path (Get-Location) "workspace/maintainer/manual-uat/models/stt/zipformer-bilingual-streaming-int8"
$env:LLM_LAB_TEST_LOCAL_STT_AUDIO = Join-Path (Get-Location) "workspace/maintainer/local-stt-validation/official-zh.wav"
.\.venv\Scripts\python.exe -m pytest tests/infrastructure/test_local_transcription.py tests/infrastructure/test_voice.py -q -s
$env:QT_QPA_PLATFORM = "windows"
.\.venv\Scripts\python.exe -m pytest tests/infrastructure/test_interview_input_runtime.py -k "real_local_stt_from_production_page" -q -s
```

真实麦克风测试另需显式 `LLM_LAB_TEST_MICROPHONE=1`，用识别替身保护环境音。用户正常使用不必执行测试命令。

纯管线定向测试：`python -m pytest tests/infrastructure/test_two_pass_transcription.py -q`。

连续停句真实 QML 验证还需 `LLM_LAB_TEST_TWO_PASS_AUDIO_ROOT` 指向获准的合成音频目录（本机 `workspace/maintainer/local-asr-comparison-20260908/audio`），再运行 `python -m pytest tests/infrastructure/test_interview_input_runtime.py -k real_two_pass_corrects_pauses -q -s`。目录需含前期生成的 `tts-intro.wav` 与 `tts-grpo.wav`，不自动录制或下载样例。
