# openWFN 0.10.1 Release Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove release/evidence inconsistencies found in the 0.10.0 audit and make the published package reproduce the same real-workflow evidence used before publication.

**Architecture:** Keep scientific kernels unchanged. Add release-consistency checks around documentation, validation metadata, package contents, and publication smoke tests; package the versioned everyday-QC corpus so public-wheel verification can execute the same bounded workflow matrix.

**Tech Stack:** Python 3.10–3.13, pytest, setuptools, GitHub Actions, PyPI trusted publishing.

**Spec:** 0.10.0 post-release audit in this conversation; authoritative release scope remains `docs/releases/0.10.0.md` until 0.10.1 metadata is prepared.

## Global Constraints

- Do not change numerical scientific algorithms or broaden scientific validation scope.
- Preserve immutable 0.10.0 tag/history; fixes land only on a new branch/release.
- Keep old regression captures, but label historical snapshots unambiguously.
- Distinguish command/resource success from scientific validation status.
- Public-PyPI verification must exercise the installed artifact, not the source checkout.

## Review Focus

- Historical validation captures must not be mistaken for current capability status.
- Installed examples must be byte-identical to the committed versioned corpus.
- Public-wheel smoke tests must work without repository-relative source files.
- Release workflow must not hard-code stale version-specific claims outside one release configuration point.
- Core installation must remain lightweight; optional interoperability/resource dependencies stay optional.

---

### Task 1: Release/evidence consistency contract

**Files:**
- Modify: `scripts/check_repository.py`
- Modify/Create tests under `tests/` following existing repository-check patterns
- Modify: `docs/project/everyday-qc-validation.md`
- Create: `validation/everyday-qc/manifest.json`

- [ ] Write failing checks for stale current-release prose and mismatched validation-manifest status.
- [ ] Verify the checks fail on the current 0.10.0-derived branch.
- [ ] Add one authoritative machine-readable manifest describing current capability status, evidence files, scope, and historical captures.
- [ ] Rewrite the project validation page so historical milestones are explicitly historical and current release status is unambiguous.
- [ ] Run repository/documentation checks and targeted tests.

### Task 2: Honest 99/99 resource wording

**Files:**
- Modify: `docs/releases/0.10.0.md` only where wording is historical clarification, or prepare equivalent 0.10.1 release wording without altering the 0.10.0 tag.
- Modify: current project/resource documentation where the benchmark is described.
- Modify/Create documentation/repository regression test.

- [ ] Add a failing documentation assertion that resource completion is not phrased as scientific validation.
- [ ] Update wording to `99/99 prescribed CLI workflows completed successfully within resource limits; scientific result status is evaluated separately`.
- [ ] Verify docs/repository checks pass.

### Task 3: Installable everyday-QC corpus

**Files:**
- Modify: `pyproject.toml`
- Modify: examples installer implementation and its tests
- Package/copy the 11 versioned Molden examples plus README/manifest under `src/openwfn/example_data/everyday-qc/` or the existing package-data convention.

- [ ] Write failing installed-package test that requests the `everyday-qc` suite and verifies all expected files/hashes.
- [ ] Verify failure before packaging changes.
- [ ] Package the corpus and extend `openwfn examples install` with a backward-compatible suite selector/default behavior.
- [ ] Build a wheel and verify installed files/hashes from the wheel.

### Task 4: Public PyPI parity smoke

**Files:**
- Modify: `.github/workflows/publish.yml`
- Modify: `scripts/benchmark_resources.py` only if needed so it can consume installed package examples rather than repository-relative paths.
- Add workflow/repository tests for the publication contract.

- [ ] Write failing workflow/repository check requiring public-PyPI install with `[interop,resources]` and a real multi-workflow corpus run.
- [ ] Refactor the benchmark entry point to accept an explicit corpus directory if repository coupling prevents installed-wheel execution.
- [ ] Before publication, run the benchmark against the built wheel and installed corpus.
- [ ] After publication, install from `https://pypi.org/simple`, install the packaged corpus, and rerun the same bounded workflow benchmark.

### Task 5: Version-driven 0.10.1 release configuration

**Files:**
- Modify: `.github/workflows/publish.yml`
- Modify: release metadata/check scripts and tests as required
- Add: `docs/releases/0.10.1.md` when release metadata is ready

- [ ] Add a failing check proving version/tag/release-note paths derive from package version rather than embedded `0.10.0` constants.
- [ ] Centralize release version/tag derivation from `pyproject.toml` and use it consistently in release creation and public-package verification.
- [ ] Keep stable-release triggering explicit and non-recursive.
- [ ] Verify build, twine check, repository checks, docs checks, and full CI before merge/publication.

### Task 6: Final verification

- [ ] Run targeted tests for each regression.
- [ ] Run the full pytest suite in supported optional-dependency CI jobs.
- [ ] Run Ruff, repository checks, documentation checks, strict MkDocs build, wheel install tests, interoperability/reference validation, browser/workbench checks, and resource benchmark.
- [ ] Inspect CI artifacts for 99 expected records, zero nonzero exits/timeouts/resource-limit failures, and preserved scientific partial/warning statuses.
- [ ] Open a PR with exact evidence and no claim that resource success itself establishes scientific validation.
