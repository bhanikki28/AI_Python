PY ?= python3
VENV := .venv
BIN := $(VENV)/bin

.PHONY: setup lint test eval dataset verify run clean

setup:
	$(PY) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip -q
	$(BIN)/pip install -e ".[dev]" -q

lint:
	$(BIN)/ruff check src tests evals

test:
	$(BIN)/pytest -q

eval:
	$(BIN)/python -m evals.run_evals

dataset:
	$(BIN)/python -m evals.generate_dataset

verify: lint test eval

clean:
	rm -rf $(VENV) .pytest_cache .ruff_cache build *.egg-info src/*.egg-info
