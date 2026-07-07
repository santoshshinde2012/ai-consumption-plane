## What & why

<!-- One or two sentences: what changed and the reason. -->

## Changes

-

## Checklist

- [ ] `ruff check .` and `pytest -q` pass locally (or via pre-commit)
- [ ] `databricks bundle validate -t dev` passes if the pipeline/bundle changed
- [ ] Product `COMMENT`s still carry owner + SLA; grants reviewed if agent tools changed
- [ ] Config changes covered by `config.validate()` / tests
- [ ] No secrets or credentials committed
- [ ] Docs (README / docstrings) updated if behavior changed
