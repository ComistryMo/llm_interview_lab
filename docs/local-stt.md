# 本地流式语音输入（当前源码）

模拟面试默认使用 **Zipformer 中英双语流式模型**。录音期间即可看到识别文字，停录后只补齐尾句。SenseVoice 的推理、下载入口和选项已经移除，没有隐藏的 SenseVoice 回退。

不需要 API Key、PyTorch、服务器或新增桌面依赖。语音在 CPU 上本地识别，文字面试官仍可使用 DeepSeek、Codex 等；本次只更新源码，不代表旧 Windows/macOS 下载包已更新。

## 使用

1. 在回答框点击「语音输入」，开始录音。正在说的话在回答框上方实时显示；可以同时手打，不会覆盖已有草稿。
2. 说完点击「完成录音」。模型补齐尾句后，把本次识别结果一次性追加到回答框，不重复追加临时结果。
3. 检查、修改，再点击「提交并继续」。识别不会自动提交、评分或生成下一问。

首次未安装时，在「语音设置」点击「下载本地模型」，约 **199 MB**。支持进度、取消和重试，已校验的完整文件复用。下载完成后可以离线使用；模型首次加载约需一段准备时间，录音仍会缓存，不丢掉开始说的话。后续录音复用已加载的模型，每次使用独立识别状态。

录音、停止和模型加载不占用面试的全局 busy 状态。录音或尾句识别期间不允许提交半成品，但可继续编辑草稿。失败时保留原 WAV，可明确点击「重试转成文字」；重试使用同一个流式模型读取已有 WAV，不会改用 SenseVoice 或自动上传。

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

单个 Qt `QAudioSource` 收音，PCM 同时写入 Profile 内 WAV 和后台队列。实际采集帧数决定时长，不用虚假墙钟。Qt 主线程每 80 ms 取音，不执行模型加载或推理；采集停止不等待 ASR。

后台调用 `OnlineRecognizer`，每段停顿确认并重置当前语音段，整场累计文本保留。结束时提供右侧上下文、`input_finished()` 并取完尾句，不重新读取整场 WAV。实时结果受 Profile、Interview、Question、Operation ID 校验，只有最终文字追加到草稿。

当前 PySide 的旧 `QAudio` 枚举与实际返回的 `QtAudio` 枚举不相等；源码使用 `QtAudio`，并在现有收音节拍中检查设备状态，避免旧 signal 签名转换错误。没有增加新的录音框架或服务。

## 本次实际验证（2026-09-08）

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
