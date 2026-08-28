PYTHON ?= python3
VENV := .venv
PYTHON_BIN := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
MPLCONFIGDIR := $(CURDIR)/.cache/matplotlib

.PHONY: setup pipeline dashboard test

setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -r requirements.txt
	npm --prefix frontend ci

pipeline:
	mkdir -p "$(MPLCONFIGDIR)"
	$(PYTHON_BIN) load_data.py
	MPLCONFIGDIR="$(MPLCONFIGDIR)" $(PYTHON_BIN) run_pipeline.py

dashboard:
	npm --prefix frontend run build
	MPLCONFIGDIR="$(MPLCONFIGDIR)" $(PYTHON_BIN) -m uvicorn backend.api:app --host $${HOST:-0.0.0.0} --port $${PORT:-8000}

test:
	mkdir -p "$(MPLCONFIGDIR)"
	npm --prefix frontend run build
	MPLCONFIGDIR="$(MPLCONFIGDIR)" $(PYTHON_BIN) -m pytest -q
