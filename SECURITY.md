# Security

## Reporting a vulnerability

Please report security issues privately via GitHub Security Advisories
(*Security → Report a vulnerability*) rather than a public issue. We aim to
acknowledge within a few business days.

## Security model of this project

- **Authorization is Unity Catalog, not application code.** Agents reach data
  through managed MCP servers with on-behalf-of-user auth, so the caller's own
  UC permissions apply on every call. The complete agent capability surface is
  the grants in [`03_agents/04_grants.sql`](03_agents/04_grants.sql) — review it
  as security-sensitive; that grant is exactly what your agents can do. Nothing
  in `eshop.silver` is reachable unless a grant says so.

- **PII is redacted in Silver, before embedding.** `config.PII_ENGINE` selects
  `regex` (baseline) or the native `ai_mask` (production, masks person/address/
  etc.). Both chunk paths — manual and `ai_prep_search` — pass through redaction,
  so raw personal data never enters an embedding. See [`lib/pii.py`](lib/pii.py).

- **Right to be forgotten is exercised, not assumed.**
  [`05_verify_and_cleanup/delete_document.py`](05_verify_and_cleanup/delete_document.py)
  deletes a document's chunks, syncs the index, and asserts it is no longer
  retrievable. Run it once before your first real deletion request.

- **Secrets never live in source.** Runtime credentials come from a Databricks
  secret scope via [`lib/secrets.py`](lib/secrets.py) (env-var fallback for CI).
  CI authenticates to Databricks via OIDC federation (`id-token: write`) or a
  repo-scoped PAT; no long-lived credentials are committed. `gitleaks` runs as a
  pre-commit hook to block accidental secret commits.

## Hardening checklist before production

- Scope [`03_agents/04_grants.sql`](03_agents/04_grants.sql) to real groups; run
  a `SHOW GRANTS` review on the `products` schema.
- Set `PII_ENGINE = "ai_mask"` and validate masked output on real documents.
- Configure OIDC federation (or rotate the PAT) for CI; enable branch protection
  requiring the CI checks.
- Run bundles as a service principal (`run_as`) in shared/prod environments.
