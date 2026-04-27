.PHONY: help setup migrate runserver shell nbshell test lint format fix rebuild docs-serve docs-build

NETBOX_DIR := /opt/netbox/netbox
VENV_PY    := /opt/netbox/venv/bin/python3
MANAGE     := $(VENV_PY) $(NETBOX_DIR)/manage.py
MODULE     := netbox_rir_manager

help: ## Show this help message
	@grep -E '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Install dev dependencies + pre-commit hooks via uv
	uv sync --extra dev
	uv run pre-commit install --hook-type pre-commit --hook-type commit-msg

migrate: ## Run database migrations
	$(MANAGE) migrate

runserver: ## Start NetBox dev server on :8009
	$(MANAGE) runserver 0.0.0.0:8009

shell: ## Open Django shell
	$(MANAGE) shell

nbshell: ## Open NetBox shell
	$(MANAGE) nbshell

test: ## Run pytest with coverage
	cd $(NETBOX_DIR) && DJANGO_SETTINGS_MODULE=netbox.settings $(VENV_PY) -m pytest $(CURDIR)/tests/ -v

lint: ## Run ruff check + ruff format --check
	uv run ruff check $(MODULE) tests
	uv run ruff format --check $(MODULE) tests

format: ## Run ruff format (write changes)
	uv run ruff format $(MODULE) tests

fix: ## Run ruff check --fix + ruff format
	uv run ruff check --fix $(MODULE) tests
	uv run ruff format $(MODULE) tests

rebuild: ## Reinstall the plugin into the NetBox venv (editable)
	$(VENV_PY) -m pip install -e .

docs-serve: ## Serve docs locally with zensical
	cd docs && uv run zensical serve

docs-build: ## Build docs (output to docs/site/)
	cd docs && uv run zensical build
