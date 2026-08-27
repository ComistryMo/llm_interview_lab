# AGT-006 — Tool-Calling Agent Loop

本题的单一函数显式包含三段职责：校验并解析 model action、通过 registry 执行工具、把 observation 或 error 追加到防御性复制的 history/trajectory。它不是只转发 API 的循环；invalid action、unknown tool、invalid arguments 和执行异常都必须转成可继续推理的结构化 observation。

## Goal

Implement one deterministic, local-only Agent data or runtime primitive.

## Interface

```python
def run_tool_calling_loop(model, registry, messages, max_steps=8) -> list[dict[str, object]]:
```

## Contract

- Operate only on defensive copies of the input message dictionaries; `model(history)` returns a local action dictionary.
- A final action is `{type: final, content: str}`; a tool action names a registry tool and argument dictionary.
- Append explicit assistant action and tool observation events; invalid actions become error observations and consume a step.
- Stop on final or raise `RuntimeError` after strict positive `max_steps`; do not implement network calls, retries, or concurrency.

## Safety boundary

These exercises execute only user-trusted local functions. They do not provide network, process, permission, or multi-tenant isolation.

## Acceptance

Run `llm-lab test AGT-006 --profile <id>`. Tests cover valid flows, malformed actions/data, deterministic ordering, state isolation, termination, and non-mutation.

## Oral defense

Explain schema validation, state transitions, invalid-action behavior, termination, replay determinism, and what production isolation remains out of scope.
