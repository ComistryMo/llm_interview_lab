# 本地语音模型对照：Qwen3-ASR 与流式 Paraformer

日期：2026-09-08。源码基线：`main / cb3d13b`。

状态：**三种候选已在本机实际推理，尚未替换应用默认模型。**

后续已完成[流式预览 + 0.6B 停句校准的隔离验证](local-stt-two-pass-validation.zh.md)，包括第一次失败的切句方式和修正后的实际结果；仍不代表正式应用已经接入。

## 结论

语音识别只考虑本地方案，不接入付费云端 ASR，不需要维护者提供服务器。本次仅联网下载公开权重和公开样例；识别使用本地路径，不调用云端推理，不读取 Profile、简历、Key 或私人录音，也没有开启麦克风。

- **优先考虑 Qwen3-ASR 0.6B 的本地准确模式**：本组技术术语改善明显，资源和速度比 1.7B 更适合当前电脑。
- **1.7B 不建议直接设为默认**：本组样例只比 0.6B 少一个字符错误，处理耗时约为其 2.35 倍。不能据此认定它对所有口音都没有优势。
- **流式 Paraformer 可作为实时候选，不宜宣称全面升级**：整体字符错误少于当前 Zipformer，但 AdamW、RMSNorm、英文片段仍有问题；这组英文样例甚至劣于基线。
- 本节仅记录单模型实验；后续“轻量流式预览 + 0.6B 停句校准”的实测见上述独立报告。两次实验都没有用转录模型之外的 LLM 改写用户回答。

这里的 Qwen 路径是 sherpa-onnx 的 **OfflineRecognizer**：收齐一段音频后识别。Qwen 模型本身支持流式，但其官方 `qwen-asr` 流式入口目前依赖 vLLM；不能把本次 ONNX 整段推理、或简单分块调用，称作已经接通原生流式。[Qwen 官方说明](https://github.com/QwenLM/Qwen3-ASR#streaming-inference)、[sherpa Qwen 部署说明](https://k2-fsa.github.io/sherpa/onnx/qwen3-asr/pretrained.html)

## 实验条件与可信边界

- Windows；i7-12850HX；16 GB RAM；Python 3.11.9；sherpa-onnx 1.13.7。
- 所有模型单独运行，使用 **CPU、2 线程、ONNX 量化权重**；没有安装新依赖，没有使用 RTX 4060、CUDA 或 vLLM。
- 开始时可用内存约 1.8–2.0 GB。1.7B 运行期间曾降到约 0.5 GB；延迟受到当时机器负载和内存压力影响，不是空载硬件基准。
- 7 条本机 Windows TTS 合成语音，共 56.645 秒、261 个归一化字符。中文使用 Microsoft Huihui Desktop，英文使用 Microsoft Zira Desktop；16 kHz、16 bit、单声道。相同 WAV 提供给全部模型，逐文件保存 SHA-256。
- 另有 4 条模型仓库公开真人语音，共 28.673 秒。**没有独立校对的参考文本，故不计算这四条的准确率。**
- 没有向模型提供参考答案、术语热词或纠错提示；Qwen 的 `max_new_tokens=256`，只验证了这些短片段。
- 字符差错率 CER 为编辑距离总和 / 参考字符总数；计算前做 NFKC、小写化并去除标点和空白，英文按字母计数。`G R P O` 与 `GRPO` 算相同，`Laura` 与 `LoRA` 不算相同。

**合成语音不等于用户口音。** TTS 对缩写的发音可能与真人不同；未完成逐音节人工校对。这些数字只能支持同样例技术对照，不能宣传为真实用户识别准确率。

## 同样例结果

处理耗时指模型加载后，不按实时速度等待、解码上述 7 条音频的墙钟总时间；不是“说完后还要等这么久”。在线模型已在说话期间计算，而 Qwen 此处在整段输入后才计算。

| 模型 / 本次接口 | 合成样例字符错误 | CER ↓ | 56.645 秒音频处理耗时 | 进程峰值工作集 |
|---|---:|---:|---:|---:|
| 当前 Zipformer / 真流式 | 41 / 261 | 15.71% | 4.25 秒 | 290 MiB |
| Paraformer 中英 / 真流式 | 32 / 261 | 12.26% | 5.83 秒 | 326 MiB |
| Qwen3-ASR 0.6B / 整段 | 5 / 261 | 1.92% | 24.58 秒 | 1773 MiB |
| Qwen3-ASR 1.7B / 整段 | 4 / 261 | 1.53% | 57.72 秒 | 2883 MiB |

峰值是 Windows 当前基准进程的 `PeakWorkingSetSize`，**不是整个应用内存、提交内存或最低配置要求**。Qwen/Paraformer 峰值取自 11 条样例，基线取自 7 条合成样例。

模型创建的单次实测耗时依次为 1.05 / 1.60 / 4.96 / 10.54 秒。Qwen 0.6B 单条推理约 2.15–4.98 秒，1.7B 约 5.39–9.59 秒，均不含模型创建。没有做冷缓存多次统计，不提供 P95 或 GPU 速度承诺。

关键观察：

- Qwen 两种规模均保留了合成样例中的 GRPO、DPO、PPO、MHA、GQA、KV Cache、AdamW、RMSNorm；空格和大小写存在差异。
- Paraformer 保留了 GRPO、DPO、PPO、GQA，但把 MHA 识别成 `maha`，AdamW 识别成 `adam double you`，RMSNorm 识别成 `rm nm`。
- 四个模型都把英文样例的 LoRA 写成 Laura。单纯增大参数量没有解决这个同音术语问题。
- Qwen 在公开真人片段中也存在省略或改写：例如同一条语音的 0.6B 输出含“频繁的”，却未保留其他模型输出中的 `frequently`；1.7B 的另一条输出明显更短。没有人工参考，不能直接把这些差异判定为谁更准确，更不能把语言更流畅当作转录更忠实。

## 真流式延迟单独测量

对同一条 10.053 秒公开真人音频，按每 100 ms 实时送入 PCM，预先加载模型：

| 模型 | 首次非空文字（从送音开始计时） | 文字更新次数 | 最后一块输入后的收尾 |
|---|---:|---:|---:|
| Zipformer | 1.12 秒 | 17 | 0.049 秒 |
| Paraformer | 1.35 秒 | 13 | 0.066 秒 |

两个在线模型都使用端点检测、0.8 秒尾静音阈值，结束时补 0.6 秒零样本并调用 `input_finished()`。这是本机文件实时回放，不是本轮麦克风或 Qt 页面验收。Paraformer 部分短句有尾字缺失，实际接入前仍需进一步检查断句、收尾与模型精度的影响。[Paraformer 官方部署页](https://k2-fsa.github.io/sherpa/onnx/pretrained_models/online-paraformer/paraformer-models.html)

## 权重与来源

| 候选 | 本次本地权重体积 | 来源 |
|---|---:|---|
| Paraformer | 226.2 MiB | [固定 HF 修订 `8e40c432`](https://huggingface.co/csukuangfj/sherpa-onnx-streaming-paraformer-bilingual-zh-en/tree/8e40c43232a1c5c66c82111efc5820d3accca11b) |
| Qwen 0.6B | 937.0 MiB + 共用 tokenizer 约 4.3 MiB | [sherpa 文档链接的转换仓库](https://modelscope.cn/models/zengshuishui/Qwen3-ASR-onnx/tree/master/model_0.6B) |
| Qwen 1.7B | 2288.6 MiB + 同一 tokenizer | [同仓库 1.7B](https://modelscope.cn/models/zengshuishui/Qwen3-ASR-onnx/tree/master/model_1.7B) |

体积为未压缩模型文件，不等于内存需求。Qwen 是第三方 ONNX 转换，不是上游原精度 PyTorch 检查点；本次结果只适用于实际下载版本。固定文件修订、大小、SHA-256 均保存在实验目录 `downloads.json`。

Paraformer 原始大文件下载失败后，使用 [ModelScope 镜像压缩包](https://modelscope.cn/models/zhaochaoqun/sherpa-onnx-asr-models)。压缩包 SHA-256 为 `61990efe6692a0ae4e80d57f699152318f4c72ffac7dab1634bda6f863c72235`；解出的 encoder、decoder 与上述固定 HF 修订 **逐文件 SHA-256 一致**。没有以名字相似的其他模型替代。

## 复验与改动范围

可复用脚本：[scripts/compare_local_asr.py](../scripts/compare_local_asr.py)。脚本只接受显式模型目录与音频清单，没有模型下载、Profile 查找、麦克风或设置修改；Python socket 连接被禁用，这不是操作系统级全进程网络审计。

本机实验数据均在 ignored 目录：

```text
workspace/maintainer/local-asr-comparison-20260908/
  downloads.json                  # 固定下载 URL、大小和哈希
  evaluation.json                 # 7 条合成语音 + 4 条公开语音
  public-evaluation.json          # 仅公开真人样例
  cases.json / make_audio.ps1     # 合成文本及现有 Windows TTS 生成方式
  models/                        # 本地权重，不进入 Git
  audio/                         # 合成音频，不进入 Git
  results/zipformer.json
  results/zipformer-public.json
  results/paraformer.json
  results/qwen-0.6b.json
  results/qwen-1.7b.json
  results/zipformer-realtime.json
  results/paraformer-realtime.json
```

本机复验示例（没有自动下载；以上文件已经就绪）：

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$asrComparisonRoot = 'workspace/maintainer/local-asr-comparison-20260908'
.\.venv\Scripts\python.exe scripts/compare_local_asr.py --kind qwen --model-root "$asrComparisonRoot/models/qwen/model_0.6B" --manifest "$asrComparisonRoot/evaluation.json" --output "$asrComparisonRoot/results/qwen-0.6b-recheck.json"
.\.venv\Scripts\python.exe scripts/compare_local_asr.py --kind paraformer --model-root "$asrComparisonRoot/models/paraformer" --manifest "$asrComparisonRoot/public-evaluation.json" --limit 1 --realtime --output "$asrComparisonRoot/results/paraformer-realtime-recheck.json"
```

换电脑时需要自行准备相同权重和显式测试音频；脚本文件头给出了最小清单格式。这里的命令是维护者复验证据，用户无须为本轮试验手动执行。

**已验证**：三个候选与原基线的真实 CPU 推理、相同 WAV 对照、两种在线模型的实时送音、权重哈希。

脚本另外通过 6 项归一化 / 编辑距离断言；三个候选分别通过 11 个输入音频 SHA 与基线一致性检查。`git diff --check` 通过，三个交付文件无尾随空白。

**本次单模型实验未验证**：用户口音 / 麦克风噪声准确率、长回答的切句与漏词、Qt 集成、流式加二次校准组合、GPU、macOS、打包。组合管线后来单独验证，见本文开头的后续报告。没有运行全量 pytest、CI、构建或付费模型请求；未修改正式语音流程、默认模型或远程选项。当前应用行为仍以[本地 STT 使用说明](local-stt.md)为准。
