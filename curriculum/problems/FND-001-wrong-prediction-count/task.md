# FND-001: Wrong Prediction Count

Implement one function:

```python
def count_wrong_predictions(label: int, predictions: list[int]) -> int:
    ...
```

The inputs model repeated predictions for one completely fictional sample.
Return how many predictions differ from `label`.

## Contract

- `label` must be a strict built-in integer: `type(label) is int`.
- `predictions` must be a strict built-in list: `type(predictions) is list`.
- Every element must be a strict built-in integer.
- `bool` is rejected for both `label` and prediction elements, even though
  Python implements `bool` as a subclass of `int`.
- `predictions` must not be empty.
- Every contract violation above raises `ValueError`.
- The input list must not be modified, including when validation fails.
- The function returns an `int` and uses clear element-oriented names.
- Do not leave unreachable statements after `return`.

Target complexity: `O(n)` time and `O(1)` auxiliary space.

## Work in your Profile

```bash
llm-lab start FND-001 --profile default
llm-lab test FND-001 --profile default
llm-lab submit FND-001 --profile default
```

Passing public tests records implementation evidence only. It does not prove
oral understanding, retention, transfer, or mastery.
