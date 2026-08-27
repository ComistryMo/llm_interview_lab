# Contributing

欢迎提交小而可验证的基础设施、文档和原创课程改进。

## 固定题 PR

一个 ready/stable Problem 必须同时提交：

1. `curriculum/catalog/*.yaml` 中唯一节点；
2. 原创 `task.md`；
3. 无答案 `starter.py`；
4. 至少五项独立公开测试；
5. H1/H2/H3 `hints.md`；
6. 前置、三维难度、技能、Runner 与 Oracle；
7. 至少四个口述问题；
8. 变式轴、不变式、常见错误、D+2/D+7；
9. 来源类型与版权确认。

目录默认只能包含这四个文件。planned 节点只写精简 Catalog 元数据，不创建空目录。不要提交 `solution.py`，也不要在测试名、错误文本或提示中泄露实现。

## 来源与隐私

可以基于论文公式、官方文档/API 和许可清晰的源码重新设计题目。不得复制第三方题面、starter、测试、提示或答案。PR 不得含真实 Profile、简历、公司/客户材料、日志、凭据、权重或本地绝对路径。

AI 可辅助起草，但贡献者必须人工核验数学、边界、测试独立性、许可证和隐私。AI 生成题至少经过 Schema/DAG、Oracle/property test、人工 Review、重复度检查和真实训练验证，才可进入公共 Catalog。

## 验证

```bash
python -m pip install -e .[dev]
llm-lab doctor
python -m pytest --collect-only -q
python -m pytest -q
python scripts/validate_external_courses.py
git diff --check
```

PyTorch 题另安装 `.[torch,dev]`，并使用私人、未跟踪的 oracle submission 运行该题公开测试。PR 请说明实际运行与未运行项，不得用 skip/xfail 隐藏回归。

实现细节见 [课程出题规范](docs/curriculum-authoring.md)。安全问题按 [SECURITY.md](SECURITY.md) 私下报告。
