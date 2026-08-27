# External Course Packs

本目录保存第三方公开课程的**兼容元数据和本项目教练层**，不镜像第三方课程内容。

- `catalog.json` 只发现已审计的 pack；
- 每个 manifest 固定上游 commit、完整 problem inventory、接口名、测试节点与资源边界；
- `NAVIGATION.md` 由 `scripts/validate_external_courses.py` 生成；
- Task Card 说明本项目 Gate、AI 帮助限制、证据、口试与间隔复测；
- 官方代码、测试、PDF、数据和模型只能由用户显式检出到 Git 忽略的 `.external/`。

外部 pack 不属于原生 `curriculum/catalog/*.yaml`，不能写入 Profile 的 `events.jsonl`，也不能把上游 pytest 全绿直接写成 `mastered`。Assignment ID 和 problem-group ID 只用于冻结的兼容清单与证据边界；安装 checkout 或阅读元数据不会开始原生任务。

`integration_status=inventory-audited` 只证明固定版本的 inventory 已审计，不证明 checkout 已安装、资源可用、前置通过或学习者已掌握。当前 pack 只能安装与 Preview，并与原生 Catalog/Workspace 流程隔离。安装前先阅读[外部课程包政策](../../docs/EXTERNAL_COURSE_PACKS.md)。

维护命令：

```bash
python scripts/validate_external_courses.py
python scripts/manage_external_course.py list
```
