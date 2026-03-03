PROJECT_NAME := docx-translator-smith
VENV         := .venv
PYTHON       := $(VENV)/bin/python
PIP          := $(VENV)/bin/pip

.DEFAULT_GOAL := help

# -----------------------------------------------------------
# Help
# -----------------------------------------------------------
.PHONY: help help-all

help: ## Show this help
	@echo "$(PROJECT_NAME) - helper targets"
	@echo
	@awk 'BEGIN {FS = ":.*##"; printf "Available targets:\n\n"} \
		/^[a-zA-Z0-9_-]+:.*##/ { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

help-all: ## Show all targets (including internal ones)
	@echo "$(PROJECT_NAME) - all targets (including internal)"
	@awk 'BEGIN {FS=":"} /^[a-zA-Z0-9_.-]+:/ {print "  "$$1}' $(MAKEFILE_LIST) | sort -u

# -----------------------------------------------------------
# Environment
# -----------------------------------------------------------
.PHONY: venv install

venv: ## Create virtualenv in .venv
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

install: ## Install package in editable mode with dev extras
	$(PIP) install -e ".[dev]"

# -----------------------------------------------------------
# Quality checks
# -----------------------------------------------------------
.PHONY: lint format mypy test

lint: ## Run Ruff linter
	$(PYTHON) -m ruff src/python tests

format: ## Format code with Black
	$(PYTHON) -m black src/python tests

mypy: ## Static type check
	$(PYTHON) -m mypy src/python

test: ## Run tests
	$(PYTHON) -m pytest

# -----------------------------------------------------------
# Build & distribution
# -----------------------------------------------------------
.PHONY: build dist-check publish

build: ## Build wheels and sdist
	$(PYTHON) -m build

dist-check: ## Validate dist/* files with twine
	$(PYTHON) -m twine check dist/*

publish: ## Upload to PyPI (remember to bump version first)
	$(PYTHON) -m twine upload dist/*

# -----------------------------------------------------------
# CLI shortcuts
# -----------------------------------------------------------
.PHONY: translate bench

translate: ## Batch translate: in_docs -> out_docs, EN → JA
	$(PYTHON) -m docx_translator.cli \
		translate-dir \
		-s EN -t JA \
		-i in_docs -o out_docs

bench: ## Benchmark translation
	$(PYTHON) -m docx_translator.scripts.bench_translation \
		--src EN \
		--tgt JA \
		--input-dir in_docs \
		--output-dir out_docs \
		-v

# -----------------------------------------------------------
# Maintenance
# -----------------------------------------------------------
.PHONY: clean deep-clean

clean: ## Remove temp files and caches
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.py[cod]" -delete
	find . -type f -name "*.so" -delete

deep-clean: clean ## Remove build artifacts too
	rm -rf dist build
	find . -type d -name "*.egg-info" -exec rm -rf {} +
