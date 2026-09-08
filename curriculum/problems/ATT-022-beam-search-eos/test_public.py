import math
import pytest


def test_greedy_and_eos(submission):
    r = submission.beam_search(lambda p: [math.log(0.2), math.log(0.8)], 1, 5, 1)
    assert r[0]["tokens"] == (1,)
    assert r[0]["finished"]


def test_eos_never_expanded(submission):
    def step(p):
        assert not p or p[-1] != 1
        return [math.log(0.4), math.log(0.6)]

    assert submission.beam_search(step, 2, 3, 1)[0]["tokens"] == (1,)


def test_lexicographic_tie(submission):
    assert [
        r["tokens"] for r in submission.beam_search(lambda p: [-0.7, -0.7], 2, 1, 9)
    ] == [(0,), (1,)]


def test_length_cutoff_not_finished(submission):
    r = submission.beam_search(lambda p: [0.0], 1, 3, 4)
    assert r == [dict(tokens=(0, 0, 0), score=0.0, finished=False)]


def test_cumulative_log_probability(submission):
    def step(p):
        return (
            [math.log(0.6), math.log(0.4)]
            if not p
            else (
                [math.log(0.1), math.log(0.9)]
                if p[0] == 0
                else [math.log(0.5), math.log(0.5)]
            )
        )

    r = submission.beam_search(step, 2, 2, 8)
    assert r[0]["tokens"] == (0, 1)
    assert r[0]["score"] == pytest.approx(math.log(0.54))
