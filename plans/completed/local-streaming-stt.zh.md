# 本地流式语音输入替换

状态：已实现并完成本机定向验收（2026-09-08）。基线 `f6074c5`，分支 `fix/dynamic-interview-full-flow-20260905`。

## 目标与范围

用户点击语音输入后，录音期间就能看到识别文字；完成录音只补齐尾句，不再整段重跑。移除 SenseVoice 推理、下载入口和选项。保留已有回答、录音和旧模型缓存，不访问真实 Profile。远程转录仍需单次授权，不自动降级、不自动提交回答。

## 当前事实与实施顺序

1. 当前 QMediaRecorder 仅输出 WAV，SenseVoice 在停录后读取文件。替换为单个 QAudioSource，PCM 同时写入本场 WAV 和后台流式识别队列。
2. 使用 sherpa-onnx 的原生 OnlineRecognizer，固定公开模型来源、哈希及许可。沿用已有模型下载界面，不新增模型管理框架。
3. Qt 主线程仅收音和展示；模型加载/解码在工作线程，停录不等待推理。实时识别是草稿，明确隔离 Profile / Session / Question / Operation。
4. 正式 InterviewPage 展示实时识别文字，完成后追加回答，不覆盖用户手打文本。取消、暂停、切题、退出丢弃迟到结果；录音仍保留，可显式重试。

## 验证与停止条件

- 只运行 local_transcription、voice、Interview QML 中直接相关的定向测试。
- 用公开中文 WAV 逐块输入实际模型，证明停录前有结果，尾句不丢失、长音频不重复；模型推理期间禁止网络。
- 正式 QML 验证实时文字、原草稿保留、四种尺寸/深浅主题、停止不卡住、重复操作及迟到回调隔离。
- 原生录音验证不识别私人环境音；真实识别另用公开音频。
- 不全量 pytest、不构建、不触发 CI，不修改面试提问逻辑或其他 Provider。

## 决策与进度

- 不用切割 WAV 反复运行离线模型冒充流式。
- 不增加 API Key、服务器、PyTorch 或新的大型依赖。
- 选定公开 Apache-2.0 中英双语 Zipformer（2023-02-20），固定修订 `98590b7…`；5 个文件共约 199 MB，实际下载并逐个 SHA 校验。没有采用许可来源不明确的候选。
- 最终记录实际证据、剩余限制；源码提交附 `[skip ci]`。

## 最终验证与复盘

分批只执行直接相关用例，失败修正后只重跑相应切片：

| 范围 | 命令选择 / 结果 |
| --- | --- |
| 模型、下载、PCM | `pytest tests/infrastructure/test_local_transcription.py tests/infrastructure/test_voice.py -q -s`：15 passed，包含真实公开音频；运行时显式指定模型/音频路径 |
| 正式页面、四尺寸、迟到结果 | `test_interview_input_runtime.py -k "dictation_click or streaming_dictation_late or voice_error_and_transcription_choices"`：9 passed |
| 正式页面 + 真实模型 | `-k real_local_stt_from_production_page`：同一原生批次中 2 passed；录音仍进行时出现实际识别文字，停录尾句约 0.5 秒 |
| 录音/远程授权/重试/生命周期 | `test_desktop_polish_core.py test_interview_input_runtime.py test_voice.py -k "recording or transcription or dictation_remote or dictation_failure or local_stt_model_download"`：19 passed |
| 停止不等待识别、暂停/退出、旧选项、原生麦克风 | `-k "streaming_stop_remains or streaming_pause_or_close or removed_stt_preference or real_microphone_start_stop_from_production_page"`：5 passed，含真实 Windows 三次录停 |
| 最后的小修复 | `test_voice.py test_interview_input_runtime.py -k "device_failure_keeps or stopped_recording_without or stop_drains or dictation_click_records"`：7 passed |

上述数量是批次结果，含针对修正的重复用例，不相加宣称独立测试总数。未运行完整 pytest、CI、打包或 Release。

原生录音发现并修复 `QAudio` / `QtAudio` 不兼容，最终三次录停耗时 66 / 59 / 60 ms，无 signal 转换报错。模型实时回放和硬件收音分开验证，硬件测试用识别替身，未识别或上传私人环境音。还修复了混合测试进程中 QCoreApplication 先于 GUI 初始化的测试夹具问题，以及录音中断后已有 WAV 无法重试的问题。

已查看正式页面浅色、深色、小窗口/放大字体截图；原始证据仅保存在 ignored 的 `workspace/maintainer/streaming-stt-validation/`。当前手动 UAT 数据根下模型已准备好，原录音/用户材料/既有未跟踪文件均保留。

使用说明和实测数字见 [本地流式语音输入](../../docs/local-stt.md)。剩余限制：未验证 macOS 实机；专有名词、噪声、口音仍需用户校正；无自动标点/数字格式化模型；其他机器首次下载依赖模型源可达。停止于本次语音输入替换，不扩展面试状态机或打包。
