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
.PHONY: help check-tools readme clean 

help: ## Show available targets
	@awk 'BEGIN {FS":.*##"; printf "\nTargets:\n"} /^[a-zA-Z0-9_.-]+:.*##/ { printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

check-tools: ## Verify required tools are present
	@if ! command -v "$(UV)" >/dev/null 2>&1; then \
		echo "Error: uv not found in PATH."; exit 127; \
	fi
	
readme: check-tools ## Render README.md
	@$(UV) run python examples/user_service.py &> examples/user_service.log
	@$(UV) run python examples/weather_service.py &> examples/weather_service.log
	@$(UV) run jinjitsu docs/README.j2.md -s examples/ > README.md
	@rm -f examples/*.log *.db
	@echo "Docs built at README.md"

clean: ## Remove all temporary files
	@rm -f examples/*.log *.db
	@echo "Cleanup complete"
