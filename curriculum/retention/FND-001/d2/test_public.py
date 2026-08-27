import pytest


def test_rate_for_mixed_predictions(submission):
    assert submission.wrong_prediction_rate(2, [2, 1, 0, 2]) == 0.5


def test_all_correct_and_all_wrong(submission):
    assert submission.wrong_prediction_rate(1, [1, 1]) == 0.0
    assert submission.wrong_prediction_rate(1, [0, 2]) == 1.0


def test_input_is_not_mutated(submission):
    values = [0, 1, 0]
    submission.wrong_prediction_rate(0, values)
    assert values == [0, 1, 0]


@pytest.mark.parametrize("label,predictions", [(True, [1]), (1, []), (1, (1,)), (1, [False])])
def test_invalid_contract_raises_value_error(submission, label, predictions):
    with pytest.raises(ValueError):
        submission.wrong_prediction_rate(label, predictions)


def test_result_is_float(submission):
    assert type(submission.wrong_prediction_rate(-1, [-1])) is float
