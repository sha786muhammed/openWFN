# Repository Trust and Publication-Readiness Cleanup Plan

**Goal:** Make the existing openWFN repository attributable, internally consistent,
contributor-ready, and suitable for later software-paper preparation without changing
scientific behavior or adding product features.

**Architecture:** Keep the current package, CLI, schemas, analyses, and version intact.
Add repository-level policy and provenance records, package the license material needed
by the existing HTML exporters, consolidate public documentation around explicit sources
of truth, and enforce those contracts with focused tests and a repository preflight.

**Tech stack:** Python 3.10–3.13, setuptools, pytest, Ruff, MkDocs Material, Markdown,
Citation File Format 1.2, GitHub community files, and existing release workflows.

**Spec:** `docs/project/specifications/2026-09-28-repository-trust-cleanup.md`

## Global constraints

- Keep the package version exactly `0.8.0a2`.
- Do not add formats, analyses, services, dependencies used at runtime, CLI commands,
  schemas, or public Python interfaces.
- Do not alter numerical results or capability classifications.
- Do not create a tag, release, or PyPI upload.
- Publish only the verified author name `Muhammed Shah Shaji`.
- Do not publish an affiliation, author email, DOI, ORCID, paper title, journal, or
  preferred paper citation.
- Preserve honest unknowns in provenance records; never reconstruct missing scientific
  history from likelihood.
- Keep HTML reports supported and the viewer/workbench available for compatibility;
  keep the workbench Experimental and secondary to machine-readable evidence.
- Do not add private paths, credentials, hostnames, or internal-assistant branding to
  tracked files.
- Keep historical release notes unless a link is broken or a present-tense statement is
  demonstrably false.

## File map

### Attribution and package contents

- Create `THIRD_PARTY_NOTICES.md` as the repository index of bundled external software.
- Create `src/openwfn/assets/3Dmol-min.js.LICENSE.txt` with the complete authoritative
  upstream license text applicable to the bundled file.
- Modify `pyproject.toml` so the root notice and both project/third-party license files
  ship through supported distribution license-file metadata, while the JavaScript remains
  package data; also expose documentation, changelog, and release project URLs.
- Modify `src/openwfn/export.py` and `src/openwfn/workbench/export.py` so generated HTML
  visibly identifies 3Dmol.js and links its name to the upstream project without adding
  a runtime network dependency.
- Extend distribution and integration tests to pin these contracts.

### Provenance and citation

- Create `examples/PROVENANCE.md` as the human-readable record for every tracked example
  input and derived file.
- Modify `src/openwfn/example_data/README.md` to point to the authoritative example record
  and retain the packaged-copy checksum.
- Modify `docs/assets/data/asset-provenance.yml` so each statement is factual and any
  unavailable generation detail is explicit.
- Modify `CITATION.cff`, `docs/citation.md`, and the README citation section so they use
  the same verified software metadata and omit the deferred paper fields.

### Contributor and repository policy

- Rewrite `CONTRIBUTING.md` as the authoritative contributor workflow.
- Create `CONTRIBUTORS.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `MAINTAINERS.md`, and
  `ROADMAP.md`.
- Create `.github/ISSUE_TEMPLATE/bug.yml`,
  `.github/ISSUE_TEMPLATE/scientific-discrepancy.yml`,
  `.github/ISSUE_TEMPLATE/feature.yml`, `.github/ISSUE_TEMPLATE/config.yml`, and
  `.github/pull_request_template.md`.
- Convert `docs/project/contributing.md` and `docs/project/security.md` into website
  guidance that links to the authoritative root policies.

### Documentation and verification

- Convert `docs/cli.md`, `docs/python-api.md`, `docs/formats.md`, and `docs/validation.md`
  into concise compatibility signposts to their authoritative reference/science pages.
- Keep `docs/quick-start.md` as a concise installed-package checklist, but remove repeated
  reference material and link to the first-analysis tutorial.
- Modify `mkdocs.yml`, README, examples documentation, HTML documentation, current API
  reference, installation guidance, and release guidance where audit evidence shows drift.
- Extend `scripts/check_docs.py` for active public-document policy checks.
- Create `scripts/check_repository.py` for package metadata, provenance, attribution,
  policy-file, and stale editable-install diagnostics.
- Extend existing tests rather than creating a second testing framework.

## Review focus

- **Unidentified 3Dmol.js build:** record its local checksum and authoritative upstream
  project/license; report the exact build version as unavailable unless checksum or Git
  history proves it. Task 1 tests the wording and checksum.
- **Unknown Gaussian generation details:** preserve `version not recorded` and `exact
  invocation not recorded` while recording file-derived method/basis/state. Task 2 tests
  that no unsupported precision is introduced.
- **Editable install pointed at another worktree:** repository preflight must report both
  the discovered editable source and remediation without deleting it. Task 6 tests this
  against a temporary simulated metadata tree.
- **Old documentation URLs:** compatibility pages must remain buildable and point to one
  authoritative page rather than silently disappearing. Task 5 tests every signpost.
- **Wheel lacks non-Python attribution files:** the built-wheel test must inspect archive
  contents rather than relying on the source tree. Task 7 exercises this directly.

---

### Task 1: Repair third-party attribution and HTML notices

**Files:**

- Create: `THIRD_PARTY_NOTICES.md`
- Create: `src/openwfn/assets/3Dmol-min.js.LICENSE.txt`
- Modify: `pyproject.toml`
- Modify: `src/openwfn/export.py`
- Modify: `src/openwfn/workbench/export.py`
- Modify: `docs/workbench.md`
- Modify: `docs/reference/formats-and-exports.md`
- Test: `tests/test_third_party_attribution.py`
- Test: `tests/integration/test_workbench_contract.py`
- Test: `tests/test_export.py`

**Interfaces:**

- Consumes: the existing vendored `src/openwfn/assets/3Dmol-min.js` and both existing HTML
  export paths.
- Produces: packaged license material and the literal generated-HTML attribution
  `Molecular rendering: 3Dmol.js (BSD-3-Clause)`.

- [ ] **Step 1: Establish the bundled asset record from evidence**

  Calculate the asset SHA-256, inspect its first-line license pointer and Git history,
  and compare it only with authoritative upstream release/tag assets. Record the exact
  version or revision only if the evidence proves it; otherwise use `version not
  recoverable from the bundled file` together with the local checksum and upstream URL.

- [ ] **Step 2: Write failing attribution tests**

  Add tests named:

  - `test_vendored_3dmol_has_full_license_and_notice`
  - `test_third_party_notice_records_vendored_checksum`
  - `test_distribution_metadata_includes_third_party_license`
  - `test_viewer_html_contains_offline_3dmol_attribution`
  - `test_workbench_html_contains_offline_3dmol_attribution`

  Assert the full license file and repository notice exist, the notice contains the
  computed 64-character checksum and authoritative upstream URL, distribution metadata
  includes `THIRD_PARTY_NOTICES.md` and `3Dmol-min.js.LICENSE.txt`, package data retains
  the JavaScript asset, and both generated documents contain the agreed attribution
  without a remote script source.

- [ ] **Step 3: Run the focused tests and confirm failure**

  Run:

  ```bash
  python -m pytest -q tests/test_third_party_attribution.py \
    tests/integration/test_workbench_contract.py tests/test_export.py
  ```

  Expected: new assertions fail because notices, license package data, and HTML
  attribution are absent.

- [ ] **Step 4: Add authoritative license and notice files**

  Reproduce the complete upstream license text, including incorporated-component terms,
  in `3Dmol-min.js.LICENSE.txt`. Write `THIRD_PARTY_NOTICES.md` with upstream project,
  use, local path, checksum, established or unavailable version, and license boundary.

- [ ] **Step 5: Package the license and add HTML attribution**

  Configure setuptools' supported distribution license-file metadata to include `LICENSE`,
  `THIRD_PARTY_NOTICES.md`, and `src/openwfn/assets/3Dmol-min.js.LICENSE.txt`. Add the exact
  attribution to the existing viewer and workbench footers without loading external
  resources or changing molecular rendering behavior. Align both documentation pages.

- [ ] **Step 6: Run focused verification**

  Run the Task 1 pytest command and `python -m ruff check src tests`. Expected: pass.

- [ ] **Step 7: Commit Task 1**

  ```bash
  git add THIRD_PARTY_NOTICES.md pyproject.toml src/openwfn/assets \
    src/openwfn/export.py src/openwfn/workbench/export.py docs/workbench.md \
    docs/reference/formats-and-exports.md tests/test_third_party_attribution.py \
    tests/integration/test_workbench_contract.py tests/test_export.py
  git commit -m "docs: restore bundled viewer attribution"
  ```

### Task 2: Make example and website-asset provenance complete

**Files:**

- Create: `examples/PROVENANCE.md`
- Modify: `examples/README.md`
- Modify: `examples/water/README.md`
- Modify: `examples/ammonia/README.md`
- Modify: `examples/methane/README.md`
- Modify: `src/openwfn/example_data/README.md`
- Modify: `docs/assets/data/asset-provenance.yml`
- Test: `tests/test_example_provenance.py`
- Test: `tests/docs/test_documentation_site.py`

**Interfaces:**

- Consumes: tracked example files, embedded FCHK records, `validation/manifest.json`, Git
  history, and current website assets.
- Produces: one factual provenance/checksum record for each distributed example file and
  one complete factual registry entry for each public website image.

- [ ] **Step 1: Inventory evidence without filling unknowns**

  Calculate SHA-256 for every tracked `.gjf`, `.fchk`, and `.xyz` example. Extract method,
  basis, charge, multiplicity, and route only where the file contains them. Compare the
  three FCHK checksums with `validation/manifest.json` and compare packaged water with the
  repository copy. Use Git history to distinguish project-created assets from imported
  ones; mark unavailable creation details explicitly.

- [ ] **Step 2: Write failing provenance tests**

  Add tests named:

  - `test_every_example_file_has_recorded_sha256`
  - `test_validation_manifest_checksums_match_examples`
  - `test_packaged_water_is_byte_identical_and_documented`
  - `test_example_provenance_preserves_unknown_gaussian_details`
  - `test_examples_overview_lists_only_existing_file_types`
  - `test_every_public_image_has_complete_factual_provenance`

  Tests must reject invented Gaussian versions/invocations and require explicit
  `not recorded` language for unavailable fields.

- [ ] **Step 3: Run focused tests and confirm failure**

  Run `python -m pytest -q tests/test_example_provenance.py
  tests/docs/test_documentation_site.py -m 'not docs'`. Expected: provenance inventory
  and current example-file-list assertions fail.

- [ ] **Step 4: Write the authoritative example record**

  Document each file, checksum, relationship, file-derived calculation metadata,
  redistribution terms, and unknown generation fields in `examples/PROVENANCE.md`.
  Correct example READMEs so paths and file lists match the repository. Make the packaged
  README a concise pointer plus checksum rather than a second conflicting history.

- [ ] **Step 5: Correct asset provenance wording**

  Retain verified transformations and licenses. Replace unsupported origin precision
  with `project-created` and explicit unavailable generation details. Do not change image
  bytes in this task.

- [ ] **Step 6: Run focused tests and commit**

  Run the Task 2 tests and `python scripts/check_docs.py --root .`. Expected: pass.

  ```bash
  git add examples src/openwfn/example_data/README.md \
    docs/assets/data/asset-provenance.yml tests/test_example_provenance.py \
    tests/docs/test_documentation_site.py
  git commit -m "docs: record example and asset provenance"
  ```

### Task 3: Professionalize citation metadata without inventing paper details

**Files:**

- Modify: `CITATION.cff`
- Modify: `README.md`
- Modify: `docs/citation.md`
- Modify: `scripts/sync_release_metadata.py`
- Modify: `tests/test_release_metadata.py`
- Modify: `tests/docs/test_documentation_site.py`

**Interfaces:**

- Consumes: `pyproject.toml` version/license/project URLs and the released tag/date already
  recorded for `0.8.0a2`.
- Produces: one verified software citation represented consistently in CFF, plain text,
  and BibTeX, plus an explicit future-paper boundary.

- [ ] **Step 1: Write failing citation-contract tests**

  Add tests named:

  - `test_citation_contains_verified_software_fields`
  - `test_active_citation_omits_deferred_identity_and_paper_fields`
  - `test_citation_guide_matches_cff`
  - `test_citation_guide_records_reproducibility_fields`
  - `test_sync_script_preserves_citation_contract`

  Assert author `Muhammed Shah Shaji`, version `0.8.0a2`, release date
  `2026-09-28`, MIT, repository, and release-tag URL. Reject the removed institutional
  affiliation, email, DOI, ORCID, preferred citation, journal, and unverified paper title
  in active citation files.

- [ ] **Step 2: Run focused tests and confirm failure**

  Run `python -m pytest -q tests/test_release_metadata.py
  tests/docs/test_documentation_site.py -m 'not docs'`. Expected: current affiliation and
  incomplete citation presentation fail.

- [ ] **Step 3: Align CFF, plain text, BibTeX, and README**

  Add valid software `type` and release URL fields to CFF. Derive the citation guide’s
  plain-text and `@software` examples from the same fields. State that paper metadata will
  follow only after archival deposit or publication and that contribution does not
  pre-assign paper authorship. Remove the affiliation from all active public copy.

- [ ] **Step 4: Tighten release-metadata synchronization**

  Keep `scripts/sync_release_metadata.py` responsible only for fields that are truly
  synchronized from project metadata. Its check mode must detect version/date/release URL
  drift without inserting affiliations or future paper fields.

- [ ] **Step 5: Run tests and commit**

  Run Task 3 tests, `python scripts/sync_release_metadata.py --check`, and
  `python scripts/check_docs.py --root .`. Expected: pass.

  ```bash
  git add CITATION.cff README.md docs/citation.md scripts/sync_release_metadata.py \
    tests/test_release_metadata.py tests/docs/test_documentation_site.py
  git commit -m "docs: establish verified software citation"
  ```

### Task 4: Add contributor, maintainer, conduct, issue, and security structure

**Files:**

- Create: `CONTRIBUTORS.md`
- Create: `CODE_OF_CONDUCT.md`
- Create: `SECURITY.md`
- Create: `MAINTAINERS.md`
- Create: `ROADMAP.md`
- Create: `.github/ISSUE_TEMPLATE/bug.yml`
- Create: `.github/ISSUE_TEMPLATE/scientific-discrepancy.yml`
- Create: `.github/ISSUE_TEMPLATE/feature.yml`
- Create: `.github/ISSUE_TEMPLATE/config.yml`
- Create: `.github/pull_request_template.md`
- Modify: `CONTRIBUTING.md`
- Modify: `docs/project/contributing.md`
- Modify: `docs/project/security.md`
- Modify: `README.md`
- Modify: `mkdocs.yml`
- Test: `tests/docs/test_repository_policies.py`

**Interfaces:**

- Consumes: verifiable Git author history, existing contribution requirements, GitHub
  private security advisories, and current validation rules.
- Produces: GitHub-recognized public policies and project-specific contributor intake.

- [ ] **Step 1: Write failing policy tests**

  Add tests named:

  - `test_required_repository_policy_files_exist`
  - `test_contributors_match_verified_git_identity_without_affiliation`
  - `test_security_policy_uses_private_reporting_and_supported_versions`
  - `test_scientific_contribution_policy_requires_evidence`
  - `test_issue_forms_cover_bug_scientific_discrepancy_and_feature_request`
  - `test_pull_request_template_covers_tests_docs_provenance_and_license`
  - `test_roadmap_has_no_promised_dates`

- [ ] **Step 2: Run policy tests and confirm failure**

  Run `python -m pytest -q tests/docs/test_repository_policies.py`. Expected: missing root
  policies and templates fail.

- [ ] **Step 3: Write root policies from verified facts**

  Name only `Muhammed Shah Shaji` as current maintainer and contributor because Git history
  supports that identity. Provide a correction path. Use a recognized code-of-conduct
  text with its source, version, and license attribution, and direct confidential concerns
  through the maintainer’s GitHub profile without publishing a private email. Use GitHub
  private security advisories for vulnerabilities.
  Distinguish security problems from scientific disagreements.

- [ ] **Step 4: Write contribution intake and restrained roadmap**

  Add issue forms and PR checklist fields that separate software bugs, numerical
  disagreements, and feature proposals. Require shareable fixtures, origin/rights,
  expected values, units, tolerances, and reference procedure for scientific claims.
  Roadmap sections may name maintenance, interoperability, validation, methods, and
  future services, but must promise no version or date.

- [ ] **Step 5: Make website policy pages summaries, not duplicates**

  Link root policies from README, MkDocs Project navigation, contributor page, and
  security/privacy page. Preserve local-data privacy guidance on the website.

- [ ] **Step 6: Run tests and commit**

  Run policy tests, documentation tests excluding the MkDocs integration test, and the
  documentation checker. Expected: pass.

  ```bash
  git add .github CODE_OF_CONDUCT.md CONTRIBUTING.md CONTRIBUTORS.md MAINTAINERS.md \
    ROADMAP.md SECURITY.md README.md docs/project mkdocs.yml \
    tests/docs/test_repository_policies.py
  git commit -m "docs: structure project contribution policies"
  ```

### Task 5: Consolidate active documentation and correct drift

**Files:**

- Modify: `docs/cli.md`
- Modify: `docs/python-api.md`
- Modify: `docs/formats.md`
- Modify: `docs/validation.md`
- Modify: `docs/quick-start.md`
- Modify: `docs/reference/cli.md`
- Modify: `docs/reference/python-api.md`
- Modify: `docs/reference/formats-and-exports.md`
- Modify: `docs/science/validation-status.md`
- Modify: `docs/installation.md`
- Modify: `docs/releasing.md`
- Modify: `docs/tutorials/geometry.md`
- Modify: `docs/tutorials/reports.md`
- Modify: `docs/guides/batch-and-reports.md`
- Modify: `docs/workbench.md`
- Modify: `mkdocs.yml`
- Modify: `scripts/check_docs.py`
- Modify: `tests/docs/test_documentation_site.py`

**Interfaces:**

- Consumes: current CLI help, parser registry, analysis registry, `openwfn.__all__`,
  package contents, validation manifests, and tracked examples.
- Produces: one authoritative active page per subject and stable signposts at older URLs.

- [ ] **Step 1: Capture current interface inventories**

  Record actual CLI command families from parser construction/help, parser suffixes from
  `DEFAULT_REGISTRY`, registered analysis names from `available_analyses()`, and public
  imports from `openwfn.__all__`. Use these results as test expectations rather than
  aspirational documentation.

- [ ] **Step 2: Write failing documentation-contract tests**

  Add tests named:

  - `test_compatibility_pages_point_to_authoritative_pages`
  - `test_active_api_reference_uses_current_schema_language`
  - `test_documented_formats_equal_registered_format_families`
  - `test_documented_named_analyses_equal_registry`
  - `test_documented_cli_families_equal_parser_choices`
  - `test_html_docs_include_attribution_privacy_and_evidence_boundary`
  - `test_documentation_contains_no_unverified_affiliation_or_private_paths`

- [ ] **Step 3: Run focused tests and confirm failure**

  Run `python -m pytest -q tests/docs/test_documentation_site.py -m 'not docs'`.
  Expected: duplicate-page and outdated-current-interface assertions fail.

- [ ] **Step 4: Convert duplicate pages into signposts**

  Point CLI, Python API, formats, and validation compatibility pages to
  `reference/cli.md`, `reference/python-api.md`, `reference/formats-and-exports.md`, and
  `science/validation-status.md`. Keep page titles and a short compatibility explanation
  so old links remain meaningful. Remove duplicate pages from navigation while retaining
  their files.

- [ ] **Step 5: Correct current documentation against inventories**

  Replace current-interface `v0.7` wording with schema/current-release wording, correct
  example paths and working directories, preserve capability boundaries, and align HTML
  pages with Task 1 attribution. Do not rewrite historical release notes.

- [ ] **Step 6: Extend documentation checks**

  Make `scripts/check_docs.py` reject active citation affiliation/paper claims, missing
  authoritative signpost targets, private paths, unresolved internal links, and documented
  commands/formats/analyses that are not in the captured inventories. Keep diagnostics
  path-specific and actionable.

- [ ] **Step 7: Run documentation verification and commit**

  Run:

  ```bash
  python -m pytest --strict-markers -m docs tests/docs
  python scripts/check_docs.py --root .
  python -m mkdocs build --strict --site-dir /tmp/openwfn-trust-site
  ```

  Expected: pass without project-authored warnings.

  ```bash
  git add docs mkdocs.yml scripts/check_docs.py tests/docs/test_documentation_site.py
  git commit -m "docs: consolidate current project guidance"
  ```

### Task 6: Add repository preflight and clean contributor setup

**Files:**

- Create: `scripts/check_repository.py`
- Create: `tests/test_repository_preflight.py`
- Modify: `CONTRIBUTING.md`
- Modify: `docs/project/contributing.md`
- Modify: `tests/README.md`
- Modify: `.github/workflows/tests.yml`
- Modify: `.github/workflows/docs.yml`
- Modify: `tests/test_ci_config.py`

**Interfaces:**

- Consumes: project version from `pyproject.toml`, optional local `*.egg-info`/distribution
  metadata, required policy/provenance paths, and tracked public-text inventory.
- Produces: `python scripts/check_repository.py --root .`, a read-only preflight returning
  zero when contracts are satisfied and actionable nonzero diagnostics otherwise.

- [ ] **Step 1: Write failing preflight tests**

  Add temporary-repository tests named:

  - `test_preflight_accepts_matching_editable_metadata`
  - `test_preflight_reports_stale_egg_info_without_deleting_it`
  - `test_preflight_reports_editable_install_from_another_checkout`
  - `test_preflight_reports_missing_policy_and_attribution_files`
  - `test_preflight_rejects_internal_branding_in_tracked_public_text`

  The mismatch diagnostic must name expected and found version/source and recommend a
  reinstall. Assert the stale file still exists after the check.

- [ ] **Step 2: Run tests and confirm failure**

  Run `python -m pytest -q tests/test_repository_preflight.py tests/test_ci_config.py`.
  Expected: missing script/workflow assertions fail.

- [ ] **Step 3: Implement the read-only preflight**

  Implement small pure check functions plus `main(argv: list[str] | None = None) -> int`.
  Accept `--root`. Read TOML with `tomllib`/`tomli`, inspect local metadata only when
  present, verify required files and public-text restrictions, print every finding to
  stderr, and never remove or rewrite a file.

- [ ] **Step 4: Document clean setup and remediation**

  Give contributors a fresh-environment sequence and an explicit reinstall command for
  stale editable metadata. Explain how to inspect ignored artifacts with
  `git status --ignored --short`; do not recommend broad destructive cleanup commands.

- [ ] **Step 5: Add preflight to CI**

  Run the preflight after editable installation in tests and documentation workflows.
  Keep current test, platform, scientific-validation, and wheel-smoke jobs unchanged.

- [ ] **Step 6: Run tests and commit**

  Run focused tests, Ruff on the new script/tests, and the preflight against the repository.
  Expected: pass after the local editable install points at this checkout and version.

  ```bash
  git add scripts/check_repository.py tests/test_repository_preflight.py \
    CONTRIBUTING.md docs/project/contributing.md tests/README.md \
    .github/workflows/tests.yml .github/workflows/docs.yml tests/test_ci_config.py
  git commit -m "chore: add repository consistency preflight"
  ```

### Task 7: Verify package contents and the complete repository

**Files:**

- Modify: `tests/test_distribution.py`
- Modify: `.github/workflows/tests.yml`
- Modify: `docs/releasing.md`
- Modify: `CHANGELOG.md` only if the project records unreleased maintenance changes

**Interfaces:**

- Consumes: all contracts produced by Tasks 1–6.
- Produces: reproducible evidence that source, wheel, installed CLI, HTML, documentation,
  validation, and repository state agree.

- [ ] **Step 1: Add built-wheel content assertions**

  Extend distribution tests or the wheel-smoke job to inspect the wheel with Python’s
  `zipfile` module. Require the vendored JavaScript, full third-party license, packaged
  example and README, package license metadata, and all public package modules. Assert the
  sdist contains root notices and policies required for redistribution/contribution.

- [ ] **Step 2: Run focused package tests**

  Run `python -m pytest -q tests/test_distribution.py`. Expected: pass after Task 1
  packaging and the new archive-inspection fixture/build step are in place.

- [ ] **Step 3: Run static and repository checks**

  ```bash
  python -m ruff check src tests scripts
  python scripts/check_repository.py --root .
  python scripts/check_docs.py --root .
  python scripts/sync_release_metadata.py --check
  ```

  Expected: all commands exit zero.

- [ ] **Step 4: Run full software and documentation tests**

  ```bash
  python -m pytest --strict-markers
  python -m mkdocs build --strict --site-dir /tmp/openwfn-trust-site
  ```

  Expected: all tests pass and the site build has no project-authored warning.

- [ ] **Step 5: Run scientific validation**

  ```bash
  python scripts/run_validation.py
  python scripts/run_external_benchmarks.py \
    --repository-only --output-dir /tmp/openwfn-trust-external
  ```

  Expected: active repository-owned cases pass; unavailable external-input cases remain
  pending rather than being promoted.

- [ ] **Step 6: Build and inspect distributions**

  ```bash
  python -m build
  python -m twine check dist/*
  python -m zipfile -l dist/openwfn-0.8.0a2-py3-none-any.whl
  ```

  Expected: build and Twine pass; archive listing includes required license, notice,
  asset, provenance, and example paths.

- [ ] **Step 7: Run clean-wheel smoke tests**

  Create a temporary Python 3.12 environment, install only the built wheel, then run:

  ```bash
  openwfn --version
  openwfn examples install ./installed-examples
  openwfn --format json --output summary.json \
    ./installed-examples/water.fchk summary
  openwfn ./installed-examples/water.fchk orbitals frontier
  openwfn ./installed-examples/water.fchk report build report.html
  openwfn ./installed-examples/water.fchk workbench workbench.html
  ```

  Assert version `0.8.0a2`, H2O summary success, frontier success, self-contained HTML,
  3Dmol.js attribution, Experimental workbench status, and no network requirement after
  installation.

- [ ] **Step 8: Inspect diff and repository state**

  Run `git diff --check`, review every active public occurrence of version, author,
  affiliation, DOI, ORCID, license, provenance, validation state, and HTML attribution,
  then run `git status --short`. Do not remove ignored user artifacts as part of review.

- [ ] **Step 9: Commit final verification adjustments**

  ```bash
  git add tests/test_distribution.py .github/workflows/tests.yml docs/releasing.md CHANGELOG.md
  git commit -m "test: enforce publication-ready package contents"
  ```

  Omit unchanged paths from `git add`. Do not create an empty commit.
