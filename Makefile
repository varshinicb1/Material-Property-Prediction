# ============================================================
# material_ai Makefile
# ============================================================
.PHONY: setup train evaluate predict app clean lint test help

PYTHON := .venv/bin/python
PIP    := .venv/bin/pip

help:
	@echo "material_ai — Available targets:"
	@echo "  make setup      — Create venv, install deps, train models"
	@echo "  make train      — Train all models"
	@echo "  make evaluate   — Evaluate models on test set"
	@echo "  make predict    — Run single prediction (default params)"
	@echo "  make app        — Launch Streamlit app"
	@echo "  make generate   — Generate synthetic dataset only"
	@echo "  make lint       — Run ruff linter"
	@echo "  make test       — Run pytest"
	@echo "  make clean      — Remove generated artifacts"

setup:
	@bash setup.sh

.venv:
	python3 -m venv .venv
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements.txt

train: .venv
	$(PYTHON) main.py train --force-regen

evaluate: .venv
	$(PYTHON) main.py evaluate

predict: .venv
	$(PYTHON) main.py predict --current 150 --voltage 15 --speed 150 --repair 0

app: .venv
	$(PYTHON) -m streamlit run app/streamlit_app.py

generate: .venv
	$(PYTHON) main.py generate

lint: .venv
	$(PYTHON) -m ruff check . --fix
	$(PYTHON) -m black . --check

test: .venv
	$(PYTHON) -m pytest tests/ -v

clean:
	rm -rf data/*.parquet
	rm -rf models/saved/*
	rm -rf results/*
	rm -rf logs/*
	rm -rf outputs/*
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
