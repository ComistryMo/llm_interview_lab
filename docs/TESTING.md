# 测试边界

## 三类命令

```bash
python -m pytest -q
```

默认健康套件只收集 `tests/infrastructure` 与 `tests/regression`，必须全绿。

```bash
python -m pytest tests/stage00/test_task_00a1.py -q
```

当前训练命令来自 `state/CURRENT_TASK.md`。实现中允许失败，但失败必须与任务状态一致。

```bash
python -m pytest -m locked tests/stage00 -q
```

锁定任务只在明确诊断或解锁时运行。不得为了 CI 全绿给未解锁任务加 xfail，也不得把已验收回归留在 locked。

## 依赖策略

基础设施不依赖 Torch。进入 Tensor 阶段后安装 `requirements-torch.txt`，并使用 `python scripts/check_environment.py --require-torch` 检查版本和导入。CUDA 测试必须独立标记且不能成为通用 CPU CI 的隐性要求。

## 课程测试原则

可见测试负责说明契约，不负责泄露算法。至少覆盖正常、边界、异常和输入不变性。未来变式应改变数据或结构，而不是只改变量名。审查必须对照任务文字，隐藏测试不能取代清楚需求。
