"""Pinned, public CPU correction assets; no downloads at import time."""

QWEN_BASE = "https://modelscope.cn/models/zengshuishui/Qwen3-ASR-onnx/resolve/"
QWEN_REV = "c69fb1666ccb59a82c09840c511a6c894e6a2482"
QWEN_LICENSE_URL = "https://huggingface.co/Qwen/Qwen3-ASR-0.6B"
VAD_LICENSE_URL = "https://github.com/snakers4/silero-vad/blob/v5.1.2/LICENSE"
VAD_FILE = "silero-vad-v5.1.2.onnx"

# Relative to the existing streaming model directory, so an upgrade reuses
# the already installed Zipformer files instead of downloading them again.
CORRECTION_FILES = (
    ("qwen/model_0.6B/conv_frontend.onnx", QWEN_BASE + QWEN_REV + "/model_0.6B/conv_frontend.onnx", 44148281,
     "d22dc4423e0940e49884e903d2ea2f7e5567c14fc1aed97e4e26d6b8f208ef9e"),
    ("qwen/model_0.6B/encoder.int8.onnx", QWEN_BASE + QWEN_REV + "/model_0.6B/encoder.int8.onnx", 182491662,
     "60748d3e6744a57c9c91e1b17424a6c2990567e8adceb0783940c03ed98fa9d9"),
    ("qwen/model_0.6B/decoder.int8.onnx", QWEN_BASE + "de9e449eb376dcb472c1ce8141fbae8d524fabbd/model_0.6B/decoder.int8.onnx", 755914231,
     "4f6885be5959ae26af3089d38ee7972c5fafbeeb1cf8d5e76eab6d8b61ca5771"),
    ("qwen/tokenizer/vocab.json", QWEN_BASE + QWEN_REV + "/tokenizer/vocab.json", 2776833,
     "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910"),
    ("qwen/tokenizer/merges.txt", QWEN_BASE + QWEN_REV + "/tokenizer/merges.txt", 1671853,
     "8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5"),
    ("qwen/tokenizer/tokenizer_config.json", QWEN_BASE + QWEN_REV + "/tokenizer/tokenizer_config.json", 12487,
     "4942d005604266809309cabc9f4e9cb89ce855d59b14681fdc0e1cc62ea26c4c"),
    (VAD_FILE, "https://raw.githubusercontent.com/snakers4/silero-vad/v5.1.2/src/silero_vad/data/silero_vad.onnx", 2327524,
     "2623a2953f6ff3d2c1e61740c6cdb7168133479b267dfef114a4a3cc5bdd788f"),
    ("LICENSE.silero.txt", "https://raw.githubusercontent.com/snakers4/silero-vad/v5.1.2/LICENSE", 1075,
     "2e63e9a38b6e8fc0c7bc37ce174caca1862870856c6daf5697cfb785e925520b"),
    ("LICENSE.qwen.txt", "https://raw.githubusercontent.com/QwenLM/Qwen3-ASR/main/LICENSE", 11343,
     "a44a6081c73ad75f0255bb2bb5cab74ef1829565a895a24e53a4f11290ab7655"),
)
