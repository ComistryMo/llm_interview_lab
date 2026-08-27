# Workspace

Workspace 是仓库内正式子系统。公共模板、Schema 和完全虚构 Demo 被跟踪；`workspace/profiles/*` 默认忽略。

每个 Profile 有 `profile.yaml`、唯一历史 `events.jsonl`，以及 submissions、generated、private_tests、reviews、cache、exports。Profile 之间没有共享状态；命令必须显式给出 `--profile`。

事件按文件物理顺序归约，timestamp 只用于复测到期计算。第一版不支持多个进程并发写同一个 events 文件。测试证据绑定 submission SHA-256；文件改变后旧 PASS 不能提交。

`start` 创建普通 attempt；`retain` 在到期且前一 Gate 通过后创建新 attempt，只复制公共 starter，不复制或展示旧答案。Review 同时记录契约、口述、代码解释、复杂度和边界。mastery 只能由完整证据链产生。

Git 隔离是隐私边界，不是备份。学习者应自行备份 ignored Profile；不要 `git add -f`。CI 只读取 `workspace/demo/`，Demo 必须含 `synthetic: true` 且不能从真实记录脱敏而来。
