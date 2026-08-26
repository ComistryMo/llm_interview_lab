.PHONY: check current test regression locked curriculum state handoff

check:
	python scripts/check_environment.py

current:
	python -m pytest tests/stage00/test_task_00a1.py -q

test:
	python -m pytest -q

regression:
	python -m pytest tests/regression -q

locked:
	python -m pytest -m locked tests/stage00 -q

curriculum:
	python scripts/validate_curriculum.py

state:
	python scripts/validate_state.py

handoff:
	python scripts/export_handoff.py --dry-run
