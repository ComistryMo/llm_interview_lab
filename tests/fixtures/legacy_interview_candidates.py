"""A pre-NumPy-expansion, Torch-only candidate pool for compatibility tests.

Keep real validated problem objects, skills and original blueprint weights.
The modern catalog has runnable pure-Python/NumPy alternatives; simply hiding
Torch no longer recreates the historical missing-coding environment.
"""
from llm_interview_lab import role_interviews


def torch_only_candidates(monkeypatch):
    original = role_interviews._coding_candidates

    def candidates(*args, **kwargs):
        return tuple(row for row in original(*args, **kwargs)
                     if role_interviews._requires_torch(row[0]))

    monkeypatch.setattr(role_interviews, "_coding_candidates", candidates)
