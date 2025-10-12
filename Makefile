# Use bash with strict mode
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:

# Strict make settings
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

# Default target
.DEFAULT_GOAL := help

# Config
UV          ?= uv
DOCS_SRC    ?= docs
DOCS_BUILD  ?= build/docs
SPHINXOPTS  ?=

# Phony targets
.PHONY: help check-tools linting typing testing examples readme clean 

define cleanup
	@rm -f examples/*.log *.db
endef

help: ## Show help
	@awk 'BEGIN{FS=":.*##"; print "\nCommands:"} \
	     /^[A-Za-z0-9_.-]+:.*##/ { sub(/\r$$/, "", $$2); printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

check-tools: ## Verify required tools are present
	@if ! command -v "$(UV)" >/dev/null 2>&1; then \
		echo "Error: uv not found in PATH."; exit 127; \
	fi

testing: check-tools ## Run tests
	@echo "> Running tests..."
	@$(UV) run pytest

linting: check-tools ## Run linting
	@echo "> Running linting..."
	@$(UV) run ruff check .

typing: check-tools ## Run type checking
	@echo "> Running type checking..."
	@$(UV) run mypy .
	@$(UV) run ty check .

examples: check-tools ## Run examples
	@echo "> Running examples..."
	@$(UV) run python examples/full_example.py &> examples/full_example.log
	@$(UV) run python examples/user_service.py &> examples/user_service.log
	@$(UV) run python examples/weather_service.py &> examples/weather_service.log
	
readme: examples ## Render README.md
	@echo "> Rendering README.md..."
	@$(UV) run python examples/full_example.py &> examples/full_example.log
	@$(UV) run python examples/user_service.py &> examples/user_service.log
	@$(UV) run python examples/weather_service.py &> examples/weather_service.log
	@$(UV) run jinjitsu docs/README.j2.md -s examples/ > README.md
	@$(call cleanup)
	@echo "> README.md rendered"

check: check-tools testing linting typing examples ## Run all checks
	@$(call cleanup)
	@echo "> All checks complete"

clean: ## Remove all temporary files
	@$(call cleanup)
	@echo "> Cleanup complete"
