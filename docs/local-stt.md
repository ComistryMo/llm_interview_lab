# 本地语音转文字（当前源码）

模拟面试的「语音输入」已提供 **SenseVoiceSmall 本地转录**。不需要 API Key、PyTorch 或独立服务器；可以搭配 DeepSeek、Codex 等文字面试官。模型在 CPU 上识别，首次下载后不联网转录。

这项更新属于当前源码，不代表 GitHub 上的旧 Windows/macOS 安装包已经更新。

## 直接使用

1. 点击回答框下方的「语音输入」，直接开始录音。默认使用本地 SenseVoiceSmall，不需要选择面试 API。
2. 说完后点击同一位置的「完成录音」，应用自动转成文字并追加到回答框，无需再点击转录。
3. 检查、修改文字后，点击「提交并继续」。

首次尚未下载模型时，点击「语音输入」会展开「语音设置」，先点击「下载本地模型」。下载量约 **240 MB**，有进度、取消和重试；开始前可打开模型许可。完成后点击「语音输入」开始，之后不再需要重复设置。已校验的完整文件会复用，未完成的单个文件重试时重新下载。

模型状态、检查 / 重新下载、远程转录选择均收在「语音设置」中。正常录音只显示状态和时长。当前是**结束录音后自动转文字**，不是说话时实时逐字显示；转录失败保留录音，可点击「重试转成文字」。

转录结果追加到可编辑草稿，不覆盖已输入的文字，不自动提交，也不作为已锁定的回答证据。原 WAV 不会因转录失败被删除或改写。没有人声、模型未下载、网络下载失败等问题会显示具体提示。

本地转录没有远程授权复选框。如果之前选择过远程服务，可在「语音设置」中切回本地；远程模式必须在每次录音前明确授权，才会在结束后发送这一次音频。重试远程发送也需重新授权。**本地失败不会自动切换远程服务。** 本地音频不会上传；你后续主动提交的回答文字仍属于面试中已经确认的 AI 发送范围。

## 安装与保存位置

源码环境安装或更新 `desktop` 依赖即可获得识别引擎：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[desktop]"
```

模型权重不随 pip 下载，在应用内单独下载。引擎与模型首次识别时才加载，不阻塞普通应用启动。

模型保存在当前应用数据根目录下的 `models/stt/sensevoice-small-int8/`。所有学习档案共用这一份公共权重，录音和答案仍分别保存在各自档案，不放进模型目录。切换数据根目录后需要下载到新目录，重新启动同一目录则直接复用。

按[桌面指南](desktop-app.md#源码运行)使用 `workspace/maintainer/manual-uat` 时，位置为：

```text
workspace/maintainer/manual-uat/models/stt/sensevoice-small-int8/
```

当前维护者 Windows 环境已安装引擎，并已在这个目录下载、校验模型。重启当前源码应用后即可使用。模型和录音都不提交 Git。

## 模型与许可

- 识别模型：FunAudioLLM / Alibaba 的 **SenseVoiceSmall**；k2-fsa 提供 int8 ONNX 转换，[官方运行说明](https://k2-fsa.github.io/sherpa/onnx/sense-voice/pretrained.html)、[ONNX 模型仓库](https://huggingface.co/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17)。当前自动识别语言，适用于中文、英文等受支持语言；不宣称各种口音都已经实测。
- 模型权重受独立的 **[FunASR Model Open Source License Agreement 1.1](https://github.com/modelscope/FunASR/blob/e19029adca384a06a2f60bd8c18cb98f1a0499aa/MODEL_LICENSE)** 约束，不应误标为本项目的 Apache-2.0 或 SenseVoice 代码的 MIT。下载即表示接受该模型许可；重新分发或商业使用前请阅读原文。
- 推理引擎：[sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)，Apache-2.0；语音分段：[Silero VAD](https://github.com/snakers4/silero-vad)，[MIT](https://github.com/snakers4/silero-vad/blob/867c2aa692646a1f1de3e94a15c9dd9f614c0acb/LICENSE)。两份模型许可随下载保存在模型目录中。

下载使用固定来源与 SHA-256；大小或哈希不匹配的文件不作为可用模型。SenseVoice 文件固定于模型仓库提交 `2365baeacb507f821a0c8120fcee3d484dba7a07`：

| 文件 | 字节数 | SHA-256 |
|---|---:|---|
| `model.int8.onnx` | 239233841 | `c71f0ce00bec95b07744e116345e33d8cbbe08cef896382cf907bf4b51a2cd51` |
| `tokens.txt` | 315894 | `f449eb28dc567533d7fa59be34e2abca8784f771850c78a47fb731a31429a1dc` |
| `silero_vad.onnx` | 643854 | `9e2449e1087496d8d4caba907f23e0bd3f78d91fa552479bb9c23ac09cbb1fd6` |

包含原模型许可指引与两份许可全文，共 **240200041 字节**。完整文件清单和许可校验值在 [`local_transcription.py`](../src/llm_interview_lab/ai/local_transcription.py)。

## 实测与限制

2026-09-07，当前 Windows 源码环境，sherpa-onnx 1.13.7、CPU 两线程：

- 下载真实模型并校验全部文件；使用官方公开中文 WAV，不使用个人录音或简历。
- 5.59 秒样例：命令行冷加载加转录约 1.7–2.7 秒；正式页面从点击到草稿完成约 7.2 秒（首次加载）和 2.6 秒（后续测试）。时间只代表本机和该样例，不是性能承诺。
- 将同一公开片段合成为 39.55 秒、六段、48 kHz 双声道录音，约 1.4 秒识别完整；同时验证中文与含空格音频路径、静音提示、原音频 SHA 不变。
- 上述推理测试禁用了网络连接，界面测试也禁止读取 Keyring；结果通过正式 QML 的后台转录路径进入可编辑回答区，不触发提交或 AI 请求。
- 已人工查看 900×620（125% 字号）与 1280×800 正式页面截图；录音区域在小窗口内可滚动。

这不是准确率基准：该短样例把「开放」误识为「开饭」，数字和后半句识别正确。专有名词、缩写、嘈杂环境和口音可能需要手工纠正。本轮没有验证 macOS 实机、真实远程 STT，也没有重建桌面安装包。

默认测试不会下载模型或采集麦克风。真实模型验证需显式指定公共测试音频：

```powershell
$env:LLM_LAB_TEST_LOCAL_STT_MODEL_ROOT = Join-Path (Get-Location) "workspace/maintainer/manual-uat/models/stt/sensevoice-small-int8"
$env:LLM_LAB_TEST_LOCAL_STT_AUDIO = Join-Path (Get-Location) "workspace/maintainer/local-stt-validation/official-zh.wav"
.\.venv\Scripts\python.exe -m pytest tests/infrastructure/test_local_transcription.py tests/infrastructure/test_transcription.py -q -s
$env:QT_QPA_PLATFORM = "windows"
.\.venv\Scripts\python.exe -m pytest tests/infrastructure/test_interview_input_runtime.py -k "local_stt or voice_error_and_transcription_choices" -q -s
```

其中 `official-zh.wav` 是维护者已下载的模型仓库 `test_wavs/zh.wav`，不会随源码提交；新环境需要先准备这一公开测试文件。用户正常使用无需运行测试命令。

## 录音计时停滞与停止卡死修复（2026-09-07）

用户在 `065f5b6` 上报告录音时长停滞，点击停止后应用未响应。正式页面的真实麦克风测试复现了停顿和原生崩溃；栈经过 `durationChanged → _voice_state_changed → stateChanged → localStt → find_spec`。单独运行同一个录音器，观察到每秒约 94 次时长通知，停止可立即返回。问题来自高频音频通知触发全页面刷新，并在 QML getter 中重复访问文件系统和检查依赖，而不是 STT 推理慢。

修复仅涉及该刷新链路：精确录音时长继续来自 Qt 音频，显示整秒改变时才通知；录音控件使用独立通知，不带动所有页面重算；模型安装状态在启动及下载结束时刷新，QML getter 只读快照。实际转录仍验证模型完整性，不靠缓存跳过校验。没有更换录音后端，也没有用虚假的墙钟计时掩盖音频问题。

修复后在隔离档案的正式 Windows 页面连续实际录停三次：时长分别 3.56、3.63、3.63 秒，停止耗时 49、50、56 毫秒，均得到 48 kHz 双声道 WAV；每次停止后都实际输入文字，前次录音文件未被改写。已查看录音中和停止后的截图。短录音只用于本机故障验证，没有转录、播放给 AI 或上传。

本次直接验证：

- `python -m pytest tests/infrastructure/test_voice.py -q`：4 passed。
- `python -m pytest tests/infrastructure/test_interview_input_runtime.py -k "local_stt or voice_error_and_transcription_choices or recording_failure_is_inline or recording_ticks_do_not_refresh_application" -q`：12 passed；真实本地模型测试使用上文两个显式路径。
- 设置 `LLM_LAB_TEST_MICROPHONE=1`、`QT_QPA_PLATFORM=windows` 后，`python -m pytest tests/infrastructure/test_interview_input_runtime.py -k "real_microphone_start_stop_from_production_page" -q -s`：1 passed，包含连续三次录停和停止后输入。

首次扩充录停测试时使用了不适用于 QQuickWindow 的 `QTest.keyClicks`，测试代码已改为逐键输入并重跑通过；这不是产品问题。未运行全量测试、CI 或打包。macOS 和其他麦克风设备仍未实机验证。

## 一键语音输入与连接页收紧（2026-09-07）

正常流程改为一次点击开始、同一个按钮结束、自动转文字。模型与远程设置默认折叠；录音中禁止提交半成品回答。自动转录等 Qt 确认 WAV 就绪后，调用原有后台转录入口，不在 GUI 线程加载模型。切换档案、问题或结束面试后，旧录音不会自动转到新上下文。之前的整秒通知与模型状态缓存修复继续保留。

连接页将 Codex 与普通 API 改为同宽纵向条目；无需 AI 的本地能力改为一行常驻说明，不再用两张内容不等长的大卡片并排占位。没有改变 API Key 的保存、修改、删除逻辑。

本轮最终通过 **25 个不同的相关用例**，分批按修改范围运行，没有全量回归：

- `test_interview_input_runtime.py -k "dictation or recording_ticks_do_not"`：新增点击录音、停止自动追加、上下文隔离、远程逐次授权、失败后保留草稿/WAV并重试；其中失败重试用例在后续批次补充验证。
- 同文件定向覆盖 `voice_error_and_transcription_choices`、`local_stt_model_download`、`real_local_stt_from_production_page`、`composer_tools`：缺失麦克风、首次下载、公开中文音频自动识别、原草稿保留。
- 同文件定向覆盖 `connections_compact`、`connections_found_codex`、`saved_key_form`、`saved_connection_card_fits`：四种窗口下对齐、Codex 入口点击、原有连接编辑与删除确认。
- `real_microphone_start_stop_from_production_page`：真实 Windows 麦克风连续三次录音，分别 3.58、3.64、3.66 秒；停止响应 85、64、77 毫秒；每次自动进入转录后仍可输入。该硬件测试使用识别函数替身，不识别环境中的私人对话；真实 SenseVoice 识别另用公开中文 WAV 验证，禁用网络及 Keyring 读取。
- `test_desktop.py::test_interview_setup_uses_profile_role_availability_and_real_report`：对应静态契约已同步新的语音入口、追加草稿行为，并纠正一个已删除的重复范围文案断言。

开发中修正了测试自身的页面属性名及多行编辑器光标定位假设，失败用例均已定向重跑通过。窗口覆盖 900×620、1080×680、1280×800、1440×900，含浅色、深色与 125% 字号；已人工查看正式页面截图。测试截图位于 ignored 的 `workspace/maintainer/dictation-ux-20260907/`，合成档案位于 pytest 临时目录；未使用真实档案，也不是实际外部用户或真实 AI 连接成功的证据。

未进行完整 pytest、CI、Windows/macOS 打包或发布；macOS 实机及真实远程 STT 本轮未验证。当前打开的源码应用不会热更新，保留当前回答后重启才能看到新交互。
