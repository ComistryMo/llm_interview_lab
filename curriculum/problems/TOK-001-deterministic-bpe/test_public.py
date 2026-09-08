import math
import pytest


def test_overlap(submission):
    m, w = submission.train_bpe({tuple("aaaa"): 1}, 1)
    assert m == [("a", "a")]
    assert w == {("aa", "aa"): 1}


def test_weighted_frequency(submission):
    assert submission.train_bpe({tuple("ab"): 3, tuple("bc"): 2}, 1)[0] == [("a", "b")]


def test_lexicographic_ties(submission):
    assert submission.train_bpe({tuple("bc"): 1, tuple("ab"): 1}, 1)[0] == [("a", "b")]


def test_empty_and_short(submission):
    assert submission.train_bpe({(): 1, ("a",): 2}, 9) == ([], {(): 1, ("a",): 2})


def test_encode_uses_merge_rank(submission):
    assert submission.encode_bpe(tuple("abab"), [("a", "b"), ("ab", "ab")]) == ("abab",)


def test_no_mutation(submission):
    v = {tuple("aa"): 2}
    submission.train_bpe(v, 3)
    assert v == {("a", "a"): 2}
