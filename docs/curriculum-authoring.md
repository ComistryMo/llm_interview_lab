# 固定课程编写指南

Catalog shards 是固定课程元数据唯一事实源；Profile events 是个人学习历史唯一事实源。不要为同一事实新增第二份手工导航、进度或题目 YAML。

## 节点状态

- `planned`：只存在于 Catalog，不创建空题目目录；
- `ready / stable`：资产完整、Schema 合法、前置存在、DAG 无环；
- validation `contract`：契约级验证，不被默认 Planner 推荐；
- `oracle / field / stable`：通过对应验证，可进入默认推荐范围。

## Coding / Debugging 题目录

```text
task.md
starter.py
test_public.py
hints.md
```

不提交 `solution.py`、参考答案、私人测试、独立状态文件或重复元数据。

题面至少定义接口、输入输出、Shape、dtype / device、异常、禁止 API、输入 mutation、复杂度与数值稳定要求。starter 只保留接口和必要 TODO，不能泄露核心答案。

公共测试只通过统一 `submission` fixture 加载学习者答案，不 import starter、不修改 `sys.path`、不硬编码 Workspace，也不复制 loader。测试彼此独立并覆盖正常、边界、异常、不变式和 non-mutation；PyTorch 题按需覆盖 shape、dtype、device、gradient、mask、稳定性、non-contiguous 与公开参考对齐。

## Case / System Design / Behavioral

```text
task.md
response_template.md
rubric.yaml
hints.md
```

Rubric 维度必须有权重和 1 / 3 / 5 分锚点，fatal issues 必须具体。评分引用回答证据，允许“不确定”，不能只做关键词匹配或用表达华丽掩盖技术错误。

## Runner 与 Oracle

Runner 是执行方式，例如 pytest；Oracle 是正确性依据，二者不能混淆。允许的 Oracle：

- `fixture_expected`；
- `closed_form`；
- `framework_reference`；
- `brute_force`；
- `cross_implementation`；
- `property_only`。

维护者答案和私有验证位于被 Git 忽略的 Workspace。Catalog 只有在 public / private / property tests 全部通过且 fingerprint 匹配时才能标记 `oracle`。

## 提示与复测

- H1：官方文档或单一概念检查；
- H2：方向与关键约束；
- H3：结构化步骤，不给完整函数；
- D+2：不展示旧答案的等价重写，接口或参数组织不同；
- D+7：典型错误调试、集成迁移、Shape / Mask / 接口变化；
- 不能只改变量名或测试数据；变式必须经过 Oracle 验证。

## 来源与版权

优先原始论文、官方文档和官方源码。可以借鉴公开定义与通用算法名，但题面、starter、测试、提示和 Rubric 必须 clean-room 原创。不得复制付费平台或许可证不明内容。

## PR 最小清单

1. Catalog 节点或合法元数据更新；
2. 原创资产；
3. 至少五个独立公共测试（适用时）；
4. H1 / H2 / H3；
5. 至少四个口述问题；
6. prerequisites、variant axes、invariants 与 common bugs；
7. 来源与版权说明；
8. Catalog / DAG / 资产 / 根 pytest 全部通过；
9. 无完整答案、真实 Profile、公司材料或本机绝对路径。

```bash
llm-lab doctor
python -m pytest --collect-only -q
python -m pytest -q
```
