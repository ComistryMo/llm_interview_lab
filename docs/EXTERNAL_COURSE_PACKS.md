# 外部课程兼容层

`curriculum/external/` 是冻结的可选兼容层，不是默认课程，也不镜像第三方作业。原生课程唯一事实源仍是 `curriculum/catalog/*.yaml`，个人历史仍是当前 Profile 的 `events.jsonl`。

## 边界

- 只登记许可清晰的公开课程版本、许可证审计、问题清单和运行资源边界；
- 官方代码、测试、PDF、数据和模型由用户显式检出到 Git 忽略的 `.external/`；
- external manifest 不注册为原生任务，不产生 implemented、retention 或 mastery 事件；
- 上游测试通过只说明上游契约通过；
- 上游学术诚信规则优先，AI 不补官方 TODO、不替跑作业、不提供答案；
- 当前 external pack 保留并冻结，本版本不扩展。

## 校验

```bash
python scripts/validate_external_courses.py
```

该脚本只验证登记信息和边界，不下载或执行第三方内容。
