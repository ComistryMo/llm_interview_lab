# 外部课程兼容层

`curriculum/external/` 是冻结的可选兼容层，不是 LEAN-V2 默认课程，也不镜像第三方作业。原生课程唯一事实源仍是 `curriculum/catalog/*.yaml`，个人历史唯一事实源仍是本地 Profile 的 `events.jsonl`。

## 当前边界

- 只登记 Stanford CS336 公开作业的固定版本、许可证审计、问题清单和运行资源边界。
- 官方代码、测试、PDF、数据和模型只会被用户显式检出到 Git 忽略的 `.external/`。
- 当前 manifest 均为 `inventory-audited`：允许查看、安装和 Preview，不允许登记为原生任务。
- 外部工具不写 Workspace，不产生 `implemented`、retention 或 mastery 事件。
- 上游测试通过只说明上游契约通过，不代表本项目的 mastery。
- 上游学术诚信规则优先；AI 帮助最高 H2，不能实现官方 TODO。

## 使用

先查看冻结清单和 machine-readable problem group：

```bash
python scripts/manage_external_course.py list
python scripts/manage_external_course.py show EXT-CS336-A1
python scripts/manage_external_course.py show-group EXT-CS336-A1-tokenizer-core --json
```

确认上游许可证、学术诚信政策和本机资源后，才显式安装一份 assignment：

```bash
python scripts/manage_external_course.py install EXT-CS336-A1 --acknowledge-policy
python scripts/manage_external_course.py status EXT-CS336-A1
python scripts/manage_external_course.py verify EXT-CS336-A1
python scripts/manage_external_course.py commands EXT-CS336-A1
```

安装器只固定 Git 来源并阻止误推到官方远端；它不安装依赖、不执行第三方代码、不自动更新或删除 checkout。A2/A4 含有可能泄露 A1 实现的材料，安装时还需显式确认 spoiler 风险。

## 版权与数据

固定来源和许可证证据记录在 `references/registry.json`。A1–A4 的审计版本存在 MIT LICENSE；A5 的固定 tree 未发现许可证，因此本仓库只登记事实性互操作信息，不复制或改编其材料。这是审计记录，不是法律意见。

不得向第三方服务上传公司、客户、个人或未公开数据。高算力、远端服务和官方完整实验未实际运行时必须写 `not_run`，不能由小型 CPU 验证推断完成。

## 维护

```bash
python scripts/validate_external_courses.py
python -m pytest tests/infrastructure/test_external_courses.py tests/infrastructure/test_manage_external_course.py -q
```

升级上游 commit 需要重新审计清单、许可证、资源和学术诚信边界；本次 LEAN-V2 MVP 不扩展该兼容层。
