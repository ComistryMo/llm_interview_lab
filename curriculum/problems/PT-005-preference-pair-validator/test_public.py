import pytest


class _StringSubclass(str):
    """Ensure the contract does not accidentally accept str subclasses."""


def _valid_pair():
    return {
        "pair_id": "toy-1",
        "prompt": " Explain the cache. ",
        "chosen": " It keeps reusable key/value states. ",
        "rejected": " It always stores the whole model. ",
        "metadata": {"source": "synthetic", "annotator": "a1"},
        "truncation": {"chosen": False, "rejected": False},
    }


def test_valid_pair_returns_content_minimizing_report(submission):
    pair = _valid_pair()
    result = submission.validate_preference_pair(pair)
    assert result["valid"] is True
    assert result["errors"] == []
    assert result["pair_id"] == "toy-1"
    assert result["lengths"] == {"prompt": 18, "chosen": 35, "rejected": 33}
    assert result["metadata"] == pair["metadata"]
    assert "chosen" not in result and "rejected" not in result


def test_unicode_equivalent_responses_are_not_distinct(submission):
    pair = _valid_pair()
    pair["chosen"] = "ＡＢＣ"
    pair["rejected"] = " abc "
    result = submission.validate_preference_pair(pair)
    assert result["valid"] is False
    assert result["errors"] == ["IDENTICAL_RESPONSES"]


@pytest.mark.parametrize("field", ["prompt", "chosen", "rejected"])
def test_empty_text_is_reported_as_a_semantic_error(submission, field):
    pair = _valid_pair()
    pair[field] = " \u2003\t"
    result = submission.validate_preference_pair(pair)
    assert result["valid"] is False
    assert result["errors"] == [f"EMPTY_{field.upper()}"]
    assert result["lengths"][field] == 0


def test_prompt_leakage_is_reported_without_rejecting_incidental_words(submission):
    pair = _valid_pair()
    pair["prompt"] = "What is caching?"
    pair["chosen"] = "What is caching? It stores reusable state."
    result = submission.validate_preference_pair(pair)
    assert result["errors"] == ["PROMPT_LEAKAGE"]

    pair["chosen"] = "Caching helps answer the question."
    assert submission.validate_preference_pair(pair)["valid"] is True


def test_asymmetric_truncation_is_invalid(submission):
    pair = _valid_pair()
    pair["truncation"] = {"chosen": True, "rejected": False}
    result = submission.validate_preference_pair(pair)
    assert result["valid"] is False
    assert result["errors"] == ["ASYMMETRIC_TRUNCATION"]


def test_multiple_semantic_errors_have_stable_order(submission):
    result = submission.validate_preference_pair(
        {
            "prompt": "Same",
            "chosen": " Same ",
            "rejected": "same",
            "truncation": {"chosen": True, "rejected": False},
        }
    )
    assert result["errors"] == [
        "IDENTICAL_RESPONSES",
        "PROMPT_LEAKAGE",
        "ASYMMETRIC_TRUNCATION",
    ]


@pytest.mark.parametrize(
    "value",
    [None, [], "text", 3, True],
)
def test_non_mapping_raises_type_error(submission, value):
    with pytest.raises(TypeError):
        submission.validate_preference_pair(value)


@pytest.mark.parametrize(
    "pair",
    [
        {"prompt": "p", "chosen": "c"},
        {"prompt": "p", "chosen": 1, "rejected": "r"},
        {"prompt": "p", "chosen": "c", "rejected": "r", "pair_id": 1},
        {"prompt": "p", "chosen": "c", "rejected": "r", "metadata": {1: "bad"}},
        {
            "prompt": "p",
            "chosen": "c",
            "rejected": "r",
            "truncation": {"chosen": False},
        },
        {
            "prompt": "p",
            "chosen": "c",
            "rejected": "r",
            "truncation": {"chosen": False, "rejected": False, "extra": False},
        },
        {
            "prompt": "p",
            "chosen": "c",
            "rejected": "r",
            "truncation": {"chosen": 0, "rejected": False},
        },
    ],
)
def test_malformed_contract_raises_value_error(submission, pair):
    with pytest.raises(ValueError):
        submission.validate_preference_pair(pair)


def test_str_subclasses_are_rejected_by_the_runtime_contract(submission):
    pair = _valid_pair()
    pair["chosen"] = _StringSubclass("answer")
    with pytest.raises(ValueError):
        submission.validate_preference_pair(pair)


def test_whitespace_only_pair_id_is_rejected(submission):
    pair = _valid_pair()
    pair["pair_id"] = " \t"
    with pytest.raises(ValueError):
        submission.validate_preference_pair(pair)


def test_metadata_and_input_are_not_mutated_or_aliased(submission):
    pair = _valid_pair()
    original = {key: value.copy() if isinstance(value, dict) else value for key, value in pair.items()}
    result = submission.validate_preference_pair(pair)
    result["metadata"]["source"] = "changed"
    assert pair == original
    assert result["metadata"] is not pair["metadata"]


def test_unknown_fields_are_ignored_without_mutating_the_pair(submission):
    pair = _valid_pair()
    pair["future_field"] = {"nested": [1, 2]}
    before = pair.copy()
    result = submission.validate_preference_pair(pair)
    assert result["valid"] is True
    assert pair == before
    assert "future_field" not in result
