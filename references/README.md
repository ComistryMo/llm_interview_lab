# References

本目录只保存外部来源的机器可读登记，不镜像第三方内容。

- `registry.json`：固定 revision、审计日期、许可证范围、设计影响和明确排除项；
- 治理规则见 [外部参考与来源治理](../docs/REFERENCE_POLICY.md)；
- Task 如何声明 Preview/review 暴露级别见 [课程元数据契约](../docs/CURRICULUM_METADATA.md)。

当前登记：

- [`datawhalechina/llm-algo-leetcode` 固定审计版本](https://github.com/datawhalechina/llm-algo-leetcode/commit/c7a81f957c170c88c01ec71dfd1a838cee90b4a4)：仅作课程发现、runtime 声明、统一校验和实验证据边界的设计参考；没有复制其教程或答案。

更新来源版本不是机械改 SHA。维护者必须重新审计受影响事实、许可证和本仓库的独立实现边界，然后运行：

```bash
python scripts/validate_curriculum.py
```
