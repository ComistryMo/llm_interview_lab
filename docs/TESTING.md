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

课程资产还有独立的离线校验入口：

```bash
python scripts/validate_curriculum.py
```

它检查 catalog、Task Card 路径、精确 pytest node、依赖 DAG、reference pin 和生成导航。修改 catalog 后先运行 `--write-navigation`，再运行普通校验；CI 只检查，不自动改文件。

## 依赖策略

基础设施不依赖 Torch。进入 Tensor 阶段后安装 `requirements-torch.txt`，并使用 `python scripts/check_environment.py --require-torch` 检查版本和导入。CUDA 测试必须独立标记且不能成为通用 CPU CI 的隐性要求。

每张任务必须声明 `runtime_profile` 和 `gpu_acceptance_policy`。`python-cpu` 不得带 CUDA 验收；`pytorch-cpu` 的公共验收必须在 CPU 可运行，GPU 只能作为补充；只有明确的 `pytorch-cuda` 任务可以把 CUDA 作为通过条件。`validated` 任务不得仍留在 `locked` 测试中。

## 课程测试原则

可见测试负责说明契约，不负责泄露算法。至少覆盖正常、边界、异常和输入不变性。未来变式应改变数据或结构，而不是只改变量名。审查必须对照任务文字，隐藏测试不能取代清楚需求。
