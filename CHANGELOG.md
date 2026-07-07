# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project uses
date-based releases.

## [Unreleased]

### Added — production hardening
- `config.validate()` fail-fast validation, `require_genie_space()`, eval regression
  thresholds, secret-scope config, and a chunk-column contract (`CHUNK_COLUMNS`).
- `lib/retry.py` (`wait_until` with capped backoff, `retry`) and `lib/secrets.py`
  (Databricks secret scope with env fallback), both unit-tested.
- Tested right-to-be-forgotten path: `05_verify_and_cleanup/delete_document.py`.
- Multi-environment Asset Bundle: `dev` / `staging` / `prod` targets, a scheduled
  refresh job, and pipeline/job failure notifications.
- Nightly retrieval-regression CI (`.github/workflows/eval.yml`) that fails below
  hit-rate / groundedness thresholds.
- Operational monitoring queries (`01_pipeline/monitoring_alerts.sql`) to wire as
  Databricks SQL Alerts, and an Auto Loader `schemaLocation`.
- Repo hygiene: pre-commit (ruff + gitleaks), `CODEOWNERS`, PR template, this changelog.
- Genie-space-as-code: `03_agents/06_create_genie_space.py`.

### Changed
- Idempotency now uses explicit existence checks (`list_*`, `tableExists`,
  `get_online_store`) instead of error-message string matching.
- Vector-index readiness wait uses typed status + capped exponential backoff.
- Dependencies pinned with compatible-release (`~=`); lock guidance documented.

## [1.0.0] — initial

- Bronze → Silver Lakeflow flow terminating in four governed data products
  (mart, feature set offline+online, hybrid vector index, metric view), exposed to
  agents via managed MCP, with MLflow 3 retrieval evaluation.
