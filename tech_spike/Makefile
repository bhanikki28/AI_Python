PY ?= python3
VENV := .venv
BIN := $(VENV)/bin

.PHONY: setup lint test eval dataset verify audit run mcp mcp-demo \
	docker-build docker-run docker-smoke clean

setup:
	$(PY) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip -q
	$(BIN)/pip install -e ".[dev]" -q

lint:
	$(BIN)/ruff check src tests evals examples

test:
	$(BIN)/pytest -q

eval:
	$(BIN)/python -m evals.run_evals

dataset:
	$(BIN)/python -m evals.generate_dataset

# Same checks CI runs on every push/PR.
verify: lint test eval

# Known-vulnerability scan of installed dependencies (the local project itself is skipped).
audit:
	$(BIN)/pip-audit --skip-editable --progress-spinner off

run:
	$(BIN)/pii-gate serve

mcp:
	$(BIN)/pii-gate-mcp

mcp-demo:
	$(BIN)/python examples/mcp_demo.py

docker-build:
	docker build -t pii-gate:local .

docker-run: docker-build
	docker run --rm --read-only -p 127.0.0.1:8000:8000 pii-gate:local

docker-smoke:
	bash scripts/smoke_test.sh

clean:
	rm -rf $(VENV) .pytest_cache .ruff_cache build *.egg-info src/*.egg-info reports
