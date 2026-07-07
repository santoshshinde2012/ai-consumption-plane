# Developer & ops entrypoints. `make help` lists targets.
.DEFAULT_GOAL := help
SRC := 01_pipeline 02_products 03_agents 04_evaluation 05_verify_and_cleanup lib config.py 00_setup

.PHONY: help install hooks lint format test compile check lock validate deploy-dev deploy-staging deploy-prod

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install:  ## Install dev dependencies
	pip install -r requirements-dev.txt

hooks:  ## Install pre-commit git hooks
	pre-commit install

lint:  ## Lint with ruff
	ruff check .

format:  ## Auto-format + fix with ruff
	ruff check --fix . && ruff format .

test:  ## Run unit tests
	pytest -q

compile:  ## Syntax-check every source file (no Spark needed)
	python -m compileall -q $(SRC)

check: lint compile test  ## Everything CI runs locally

lock:  ## Pin exact runtime versions into requirements.lock (needs `uv`)
	uv pip compile requirements.txt -o requirements.lock

validate:  ## Validate the Asset Bundle (dev)
	databricks bundle validate -t dev

deploy-dev:  ## Deploy the bundle to dev
	databricks bundle deploy -t dev

deploy-staging:  ## Deploy the bundle to staging
	databricks bundle deploy -t staging

deploy-prod:  ## Deploy the bundle to prod
	databricks bundle deploy -t prod
