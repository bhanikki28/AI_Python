PY ?= python3
VENV := .venv
BIN := $(VENV)/bin

.PHONY: setup lint test eval verify run clean

setup:
	$(PY) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip -q
	$(BIN)/pip install -e ".[dev]" -q

lint:
	$(BIN)/ruff check src tests

test:
	$(BIN)/pytest -q

eval:
	@echo "evals land in Phase 2"

verify: lint test eval

clean:
	rm -rf $(VENV) .pytest_cache .ruff_cache build *.egg-info src/*.egg-info
