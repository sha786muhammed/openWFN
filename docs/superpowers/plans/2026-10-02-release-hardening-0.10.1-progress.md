# SDD ledger — plan: docs/superpowers/plans/2026-10-02-release-hardening-0.10.1.md

## Pre-flight rulings

- Tasks 1–5 share release/version/corpus metadata. The version stayed at 0.10.0 through the RED phase and was promoted to 0.10.1 only after the release-drift regressions existed.
- Direct container network access to GitHub is unavailable. Source edits use the connected GitHub API and authoritative RED/GREEN verification uses branch CI. No local-test claim is made without executable evidence.
- Reuse the existing canonical `validation/manifest.json`; do not create a second competing current-status manifest.
- Preserve the `install_examples()` return contract: callers still receive the historical top-level `water.fchk` tuple, while the complete release corpus is installed under `everyday-qc/`.
- Do not change numerical scientific kernels, formulas, result/model schemas, or scientific tolerances in this patch.
- Preserve historical validation captures and release notes; make their role explicit rather than rewriting past evidence as though it had always carried the current status.

## RED evidence

Initial hardening contract commit: `acd62dbd9cf1eed3b718c1e94789d0b81448f860`.

GitHub Actions run `37056586886`, Python 3.12 pytest job `111002676741`, produced **6 failed, 640 passed, 189 skipped, 1 deselected**. The six failures were the newly introduced release-hardening checks: stale release prose, missing current manifest contract, missing 0.10.1 resource wording, hard-coded publication logic, missing packaged corpus globs, and repository-coupled resource benchmarking. Existing scientific/reference jobs remained green in that RED stage.

## Implemented fixes

- Replaced the stale development handoff with a current everyday-QC validation/evidence page.
- Extended `validation/manifest.json` with current 0.10.1 capability status, the current eleven-molecule corpus, the 99-command resource contract, explicit non-authoritative historical captures, and a note separating the legacy FCHK registry from current Molden coverage.
- Added 0.10.1 release notes, changelog/citation/security/install/release-history updates, and synchronized current handbook/README navigation.
- Removed stale development/Experimental labels from public method/CLI pages where the documented stable scope is now Validated; preserved conditional/Experimental status for results whose own diagnostics fail.
- Packaged byte-identical copies of all eleven everyday-QC Molden inputs plus corpus documentation/manifest under `openwfn.example_data`.
- Extended `openwfn examples install` to install the full corpus without changing its historical Python return contract.
- Added distribution tests requiring the complete corpus in the installed package and built wheel.
- Added `--examples-dir` to the resource benchmark, require exactly eleven inputs and 99 records, and hash the actually imported openWFN package rather than repository source files.
- Reworked stable publication into one version-driven path. Release metadata comes from `pyproject.toml`; the release commit subject must be exactly `release:<version>`.
- Removed publication path filters so a deliberate empty approval commit can trigger release. The required Tests, Documentation, Security, and Chromium workflows all run on every main push, so the exact-commit gate remains satisfiable.
- Built-wheel verification installs `[interop,resources]`, installs the packaged corpus, and reruns the 99-command benchmark.
- Public-PyPI verification downloads the exact release with the same extras, installs the same corpus, reruns the same 99-command benchmark, and retries briefly for index propagation.
- Preserved the scientific distinction that 99/99 command/resource completion is **not** scientific validation.

## Review findings fixed during implementation

- Corrected the GitHub Actions bot email identity.
- Removed a `paths:` publication filter that would have made an explicit empty release-approval commit ineffective.
- Confirmed `scripts/release_gate.py` waits only for `Tests and quality`, `Documentation`, `Security audit`, and `Offline workbench browser validation`; it does not wait on the publish workflow itself.
- Confirmed all four required workflows run on every main push, including an empty release-approval commit.
- Synchronized the source and packaged everyday-QC README so PyPI users are not told that the corpus is source-only.

## Final verification rule

The exact branch-head CI after this ledger commit is the completion authority. Do not describe the branch as complete or ready to merge until all required exact-head workflows pass. The PR remains draft and no tag, PyPI upload, GitHub Release, or merge is performed by this implementation work.
