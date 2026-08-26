# 训练状态模型

`state/TASK_LEDGER.jsonl` 是历史唯一事实源。每行一个不可修改的事件；`CURRENT_TASK.md` 的隐藏 JSON 块是最新任务快照，校验器要求两者完全一致。`PROGRESS.md`、handoff 和文字说明是派生视图。

## 状态

```text
not_started
  → attempted
  → implemented
  → reviewed
  → retained_48h
  → retained_7d
  → mastered
```

任一实现、review、复测或回归发现关键问题时进入 `needs_revision`，修订需开始新的 attempt。`demonstration_only` 是 attempt 元数据，不是状态。

| 状态 | 证据含义 |
|---|---|
| `not_started` | Task 已登记，尚无真实尝试 |
| `attempted` | 已开始且记录帮助等级 |
| `needs_revision` | 有关键需求、测试、解释或 retention 问题 |
| `implemented` | 实现、文字要求和必要测试通过 |
| `reviewed` | 正式代码审查与规定口述通过 |
| `retained_48h` | review 后至少 48 小时，H0 闭卷复写通过 |
| `retained_7d` | review 后至少 7 天，H0 结构变式通过 |
| `mastered` | review 后至少 21 天，H0 综合迁移或面试级验收通过 |

## 时间语义

除一次性 `legacy_import` 外，所有新事件必须使用带明确时区的 RFC3339 `recorded_at`；naive 时间与未知偏移 `-00:00` 被拒绝。48 小时是精确 `timedelta(hours=48)`，不是“隔两个日期”。D+7 和 D+21 同理按实际经过时间计算。

旧仓库只能用 `recorded_on` 导入已知日期，`recorded_at` 必须为 null。legacy review 不会建立 retention 计时起点，避免为历史记录编造时刻。

## 帮助与独立证据

- H5 必须 `demonstration_only=true`；
- advancement 需要 passing test artifact；review 与 mastery 还需要口述通过；
- retention/mastery 必须 H0、非 demonstration、使用未出现过的 `variant_id`；
- H4/H5 使用后不能在同一 attempt 中伪装成 H0；必须用新的独立变式清偿演示债务；
- evidence 只接受存在于仓库内的普通相对文件，拒绝绝对路径、`..`、符号链接和 reparse path。

## 合法事件主链

| 事件 | 转换 |
|---|---|
| `task_registered` | none → not_started |
| `attempt_started` | not_started/needs_revision → attempted |
| `implementation_verified` | attempted → implemented |
| `review_passed` | implemented → reviewed |
| `retention_48h_passed` | reviewed → retained_48h |
| `retention_7d_passed` | retained_48h → retained_7d |
| `mastery_passed` | retained_7d → mastered |

对应 failed、abandoned、regression 事件进入 `needs_revision`。`note` 只能保持状态。`legacy_import` 仅用于一次性迁移，不能追加到已有 task。

## 校验

```bash
python scripts/validate_state.py
python scripts/validate_state.py --json
python scripts/validate_state.py --base-ledger <previous-ledger-copy>
```

校验拒绝未知字段、重复 JSON key、重复 event/attempt/variant、断裂状态链、倒序时间、危险 evidence 路径、Markdown 漂移和被修改的历史前缀。记录新事件只能 append；不要编辑旧行来“修正”成绩，错误记录应以新事件解释。
