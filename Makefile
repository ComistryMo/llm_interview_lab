.PHONY: check current test regression locked curriculum external state handoff verify

check:
	python scripts/check_environment.py

current:
	python scripts/run_current_task.py

test:
	python -m pytest -q

regression:
	python -m pytest tests/regression -q

locked:
	python -m pytest -m locked tests/stage00 -q

curriculum:
	python scripts/validate_curriculum.py

external:
	python scripts/validate_external_courses.py

state:
	python scripts/validate_state.py

handoff:
	python scripts/export_handoff.py --dry-run

verify: curriculum external state test
