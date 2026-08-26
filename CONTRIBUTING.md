# Contributing

感谢你改进 LLM Interview Lab。这个仓库优先接受小而可验证的改动，不接受为“铺路线”批量生成的空任务。

## 贡献类型

- 基础设施或文档：说明用户问题、变更范围和验证命令；
- Curriculum Task：必须有唯一 ID、前置任务、目标、starter、可见测试、边界、提示阶梯、D+2/D+7 变式；
- 测试修复：说明原需求、此前漏检和为什么不会泄露答案；
- 安全问题：按 [SECURITY.md](SECURITY.md) 私下报告。

完整学员答案、真实训练记录、雇主/客户材料、模型权重、日志和未经验证的 AI 批量内容不属于可接受贡献。

## 本地验证

```bash
python -m pip install -r requirements.txt
python scripts/check_environment.py
python -m pytest -q
python scripts/validate_state.py
python scripts/export_handoff.py --dry-run
```

涉及可选 PyTorch 任务时，再安装 `requirements-torch.txt` 并运行对应定向测试。不要通过 skip 或 xfail 隐藏一个已解锁回归。

## Pull request 要求

PR 应只解决一个清楚的问题，并写明：

1. 为什么需要改变；
2. 改了哪些权威文件；
3. 运行过哪些测试和结果；
4. 是否使用 AI，以及贡献者如何核验准确性；
5. 隐私、许可证和答案泄露检查结果。

课程贡献必须保持 `src/` starter 与参考答案分离。H4/H5 内容不能藏在测试名、错误消息、注释或提示文件里。

## Git 习惯

- 从最新 `main` 建短生命周期分支；
- 使用清晰、范围单一的提交；
- 不重写他人历史；
- 提交前检查 `git diff --check` 和 staged 文件清单；
- 贡献即表示你有权按 Apache-2.0 提交这些内容。
