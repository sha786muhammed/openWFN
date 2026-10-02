# SDD ledger — plan: docs/superpowers/plans/2026-10-02-release-hardening-0.10.1.md

Pre-flight: Tasks 1–5 share release/version/corpus metadata. Ruling: current `pyproject.toml` version remains 0.10.0 during hardening; prepare 0.10.1 metadata only after regression checks are in place, so tests prove the drift before version promotion.

Environment ruling: direct container network access to GitHub is unavailable. Source edits use the connected GitHub API and authoritative RED/GREEN verification uses branch CI. No local-test claim will be made without executable evidence.
