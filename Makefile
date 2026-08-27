.PHONY: doctor test collect external verify

doctor:
	llm-lab doctor

collect:
	python -m pytest --collect-only -q

test:
	python -m pytest -q

external:
	python scripts/validate_external_courses.py

verify: doctor collect test external
