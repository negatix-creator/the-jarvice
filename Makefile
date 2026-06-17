.PHONY: help test lint coverage clean install

PYTHON ?= python3
VENV ?= ~/.the-jarvice/venv
PIP ?= $(VENV)/bin/pip
PYTEST ?= $(VENV)/bin/pytest

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

venv: ## Create virtual environment
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip

install: venv ## Install the-jarvice in development mode
	$(PIP) install -e ".[dev]"

test: ## Run all tests
	$(PYTEST) tests/ -v --tb=short

test-sprint: ## Run sprint-specific tests (pass SPRINT=001|002|003|004)
	$(PYTEST) tests/test_sprint$(SPRINT).py tests/test_e2e.py -v --tb=short

lint: ## Run linter
	$(VENV)/bin/ruff check the_jarvice/ tests/

format: ## Run formatter
	$(VENV)/bin/ruff format the_jarvice/ tests/

coverage: ## Run tests with coverage report
	$(PYTEST) tests/ --cov=the_jarvice --cov-report=term-missing --cov-report=html

clean: ## Remove build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

doctor: ## Run the-jarvice doctor
	$(VENV)/bin/the-jarvice doctor

status: ## Show the-jarvice status
	$(VENV)/bin/the-jarvice status

version: ## Show version
	@cat VERSION