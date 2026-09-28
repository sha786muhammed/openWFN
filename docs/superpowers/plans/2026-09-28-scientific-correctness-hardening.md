# Scientific Correctness Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate silent scientific-correctness failures in openWFN 0.8.0 for ECP/ghost atoms, population and density conservation, post-HF density provenance, unrestricted/ROHF frontiers, cube validation, and batch status handling while preserving current public workflows.

**Architecture:** Extend the existing typed model with source-faithful nuclear-charge and density-source metadata, centralize scientific expectations/validation in a small helper module, and propagate validated status/warnings through the current services, registry, API, CLI, and batch layers. Keep existing public method names and result fields, add new metadata fields where needed, and pin every corrected failure mode with a regression test before implementation.

**Tech Stack:** Python 3.10+, NumPy, pytest, argparse CLI, current `ResultRecord`/registry/batch architecture.

**Spec:** `docs/superpowers/specs/2026-09-28-scientific-correctness-hardening-design.md`

## Global Constraints

- Preserve existing public calls such as `openwfn.load`, `calc.orbitals`, `calc.population`, `calc.density`, registered analyses, and current CLI command families.
- Keep `RESULT_SCHEMA_VERSION` and `BATCH_SCHEMA_VERSION` readable by existing 0.8.0 consumers unless a schema break becomes unavoidable.
- Use FCHK source records as authoritative where available; fallbacks must be explicit and warned.
- Scientific consistency failures with useful numbers return `status="partial"`, not silent `success` and not hard `failed` unless the analysis cannot produce a meaningful result.
- Population conservation tolerance: `1e-6 e`.
- Density relative validation tolerance for nonzero targets: retain `5e-3` (0.5%).
- Zero-target spin-density absolute tolerance: `5e-3 e`.
- Ghost detection tolerance for effective nuclear charge: `1e-12`.
- Löwdin near-linear-dependence warning threshold: smallest positive overlap eigenvalue `< 1e-8` or condition number `> 1e10`.
- Do not claim post-SCF density support until an actual post-SCF FCHK density record is parsed and selected.
- Keep water/benzene behavior numerically unchanged within existing test tolerances.

## Review Focus

- FCHK input with missing `Nuclear charges`: analyses must fall back deterministically and expose a warning rather than invent ECP/ghost semantics; Task 1 tests this.
- Non-Aufbau/fractional occupations: current FCHK occupation synthesis must be identified as electron-count filling and unsupported cases must not be silently represented as validated; Task 5 tests the exposed metadata/warning behavior.
- A calculation where every parsed orbital is occupied: frontier analysis must fail clearly because no LUMO exists; Task 5 retains and extends this boundary test.
- Batch containing only `partial` analysis results: the input record must be `partial`, never `error`; Task 6 tests this exact case.
- Chunk boundaries in large grids: chunked and unchunked density values/integrals must agree within floating-point tolerance; Task 7 tests multiple chunk sizes including a non-divisor of point count.

---

### Task 1: Source-faithful nuclear charge, electron-count, and density-source model

**Files:**
- Modify: `src/openwfn/model.py`
- Modify: `src/openwfn/parsers/gaussian/fchk.py`
- Create: `src/openwfn/scientific.py`
- Modify: `tests/unit/test_model.py`
- Modify: `tests/parsers/test_gaussian_fchk.py`
- Create: `tests/fixtures/scientific/ecp_minimal.fchk`
- Create: `tests/fixtures/scientific/ghost_minimal.fchk`
- Create: `tests/fixtures/scientific/post_hf_scf_density.fchk`

**Interfaces:**
- Produces: `Atom.nuclear_charge: float | None = None` while preserving existing `Atom(atomic_number, coordinates)` calls.
- Produces: `DensityMatrix.source: str | None = None`; FCHK `Total SCF Density`/`Spin SCF Density` set `source="scf"`.
- Produces: `effective_nuclear_charge(atom: Atom) -> float`, `is_ghost_atom(atom: Atom, tolerance: float = 1e-12) -> bool`.
- Produces: `ElectronExpectation(value: float, source: str, warnings: tuple[str, ...])` and `expected_electron_count(data: CalculationData, kind: str) -> ElectronExpectation`.
- Produces: `orbital_reference_kind(data: CalculationData) -> Literal["restricted_closed_shell", "restricted_open_shell", "unrestricted", "unknown"]`.

- [ ] **Step 1: Write failing model/parser tests**
  - Assert ECP fixture parses atomic number 14 with `nuclear_charge == 4.0`.
  - Assert ghost O parses atomic number 8 with `nuclear_charge == 0.0`.
  - Assert missing `Nuclear charges` leaves `nuclear_charge is None` and adds one provenance fallback warning.
  - Assert FCHK `Number of electrons` is preferred by `expected_electron_count(..., "total")`.
  - Assert alpha/beta/spin expectations come from source electron-count records.
  - Assert SCF density matrices carry `source == "scf"`.

- [ ] **Step 2: Run focused tests and confirm failure**
  - Run: `pytest tests/unit/test_model.py tests/parsers/test_gaussian_fchk.py -q`
  - Expected: new nuclear-charge/source assertions fail on current 0.8.0 behavior.

- [ ] **Step 3: Extend `Atom` and `DensityMatrix` without breaking positional construction**
  - Add optional fields after current required fields and validate finite nuclear charge when present.

- [ ] **Step 4: Parse `Nuclear charges` and source metadata in `parse_fchk`**
  - Require `Nuclear charges` length to equal atom count when present.
  - Set parser provenance warning only when the source record is absent.
  - Tag parsed SCF density matrices with `source="scf"`.

- [ ] **Step 5: Implement `src/openwfn/scientific.py` helpers**
  - Implement exact interfaces above.
  - Total electron expectation precedence: `Number of electrons` -> sum effective nuclear charges minus net charge -> atomic-number fallback with warning.
  - Spin expectation allows zero.

- [ ] **Step 6: Re-run focused tests**
  - Run: `pytest tests/unit/test_model.py tests/parsers/test_gaussian_fchk.py -q`
  - Expected: PASS.

- [ ] **Step 7: Commit**
  - `git commit -am "fix: preserve source nuclear charges and electron metadata"`

---

### Task 2: Population correctness, conservation enforcement, and Löwdin diagnostics

**Files:**
- Modify: `src/openwfn/analysis/population.py`
- Modify: `src/openwfn/services.py`
- Modify: `tests/unit/test_population.py`
- Modify: `tests/integration/test_python_api.py`

**Interfaces:**
- Consumes: `effective_nuclear_charge`, density `source` from Task 1.
- Produces: `PopulationResult` values computed with effective nuclear charges.
- Produces: population `ResultRecord.data["density_source"]`.
- Produces: Löwdin diagnostics in result data: `overlap_min_eigenvalue`, `overlap_condition_number`.

- [ ] **Step 1: Write failing regression tests**
  - ECP and ghost population charges use effective nuclear charges and sum to net molecular charge when the density is consistent.
  - A deliberately inconsistent population result with `conservation_error > 1e-6` returns `status="partial"`, `validation_status="Experimental"`, and a conservation warning.
  - A consistent population remains `success`.
  - A near-linearly-dependent Löwdin overlap returns values plus warning/`partial`, not silent clean success.
  - A post-HF fixture using SCF density includes `density_source="scf"` and a warning naming SCF density.

- [ ] **Step 2: Run focused tests and confirm failure**
  - Run: `pytest tests/unit/test_population.py tests/integration/test_python_api.py -q`

- [ ] **Step 3: Replace atomic-number charge subtraction with effective nuclear charges**
  - Keep public `mulliken_population(...)` and `lowdin_population(...)` signatures unchanged.

- [ ] **Step 4: Add centralized population validation in `services.population_analysis`**
  - Use tolerance `1e-6 e`.
  - Merge density-source/post-HF warnings without duplicates.
  - Set `partial` only for failed scientific consistency/conditioning checks, not informational provenance warnings.

- [ ] **Step 5: Add Löwdin conditioning diagnostics**
  - Calculate minimum positive eigenvalue and condition number from the overlap eigenspectrum.
  - Warn/partial at the global thresholds.

- [ ] **Step 6: Re-run focused tests**
  - Expected: PASS.

- [ ] **Step 7: Commit**
  - `git commit -am "fix: enforce population conservation and lowdin diagnostics"`

---

### Task 3: Density validation semantics and evidence-based cube status

**Files:**
- Modify: `src/openwfn/analysis/density.py`
- Modify: `src/openwfn/services.py`
- Modify: `tests/unit/test_density.py`
- Modify: `tests/unit/test_exporters.py`
- Modify: `tests/cli/test_commands.py`

**Interfaces:**
- Consumes: `expected_electron_count` and density source from Task 1.
- Produces: `IntegrationResult` with `absolute_error`, `relative_error: float | None`, `error_metric: Literal["absolute", "relative"]`, and `passed: bool`.
- Produces: density/cube result data fields `expected_electrons`, `absolute_error`, `relative_error`, `error_metric`, `density_source`.

- [ ] **Step 1: Write failing density and cube tests**
  - Closed-shell singlet spin density with expected value 0 validates by absolute error and does not raise.
  - Nonzero total/alpha/beta targets retain relative-error validation.
  - Accurate cube grid is `Validated`/`success`.
  - Intentionally coarse/truncated cube is still written but returns `Experimental`/`partial` with warning.
  - Post-HF SCF density integration names its source and warns.

- [ ] **Step 2: Run focused tests and confirm failure**
  - Run: `pytest tests/unit/test_density.py tests/unit/test_exporters.py tests/cli/test_commands.py -q`

- [ ] **Step 3: Refactor `integrate_density` for zero-target semantics**
  - Permit expected electron count 0 only for validation callers that request absolute-error semantics.
  - Use `5e-3 e` absolute tolerance when target magnitude <= `1e-12`.

- [ ] **Step 4: Replace `_expected_electrons` in `services.py` with Task 1 helper**
  - Preserve existing result field `expected_electrons`.
  - Add expectation source/warnings.

- [ ] **Step 5: Validate the exact grid used by `density_cube_export` before assigning status**
  - Do not regenerate a second grid.
  - Write requested cube even when numerical validation is partial.

- [ ] **Step 6: Re-run focused tests**
  - Expected: PASS.

- [ ] **Step 7: Commit**
  - `git commit -am "fix: validate density and cube electron conservation"`

---

### Task 4: ECP/ghost-safe ESP, cube headers, and molecular summaries

**Files:**
- Modify: `src/openwfn/analysis/electrostatics.py`
- Modify: `src/openwfn/exporters/cube.py`
- Modify: `src/openwfn/services.py`
- Modify: `tests/unit/test_electrostatics.py`
- Modify: `tests/parsers/test_gaussian_cube.py`
- Modify: `tests/unit/test_analysis_registry.py`

**Interfaces:**
- Consumes: `effective_nuclear_charge` / `is_ghost_atom` from Task 1.
- Produces: summary fields `centers`, `physical_nuclei`, `ghost_centers`, `bond_source` while retaining existing `atoms`, `formula`, `bond_count`, `fragments` fields.

- [ ] **Step 1: Write failing ECP/ghost tests**
  - Nuclear ESP uses ECP effective charge 4 instead of atomic number 14.
  - Ghost nuclear ESP contribution is zero.
  - Cube atom line keeps element identity integer but writes effective charge in the cube nuclear-charge column.
  - Ghost summary formula/COM/bond inference/fragments exclude ghost center while `centers` still counts it.
  - Ordinary water summary values remain unchanged and report `bond_source="covalent-radius heuristic"`.

- [ ] **Step 2: Run focused tests and confirm failure**
  - Run: `pytest tests/unit/test_electrostatics.py tests/parsers/test_gaussian_cube.py tests/unit/test_analysis_registry.py -q`

- [ ] **Step 3: Use effective charges in nuclear ESP and cube serialization**

- [ ] **Step 4: Make `molecular_summary` ghost-aware**
  - Build physical-atom arrays and remap inferred physical bonds before fragment counting.
  - Add an informational ghost-filter warning without forcing `partial` solely because a ghost exists.

- [ ] **Step 5: Re-run focused tests**
  - Expected: PASS.

- [ ] **Step 6: Commit**
  - `git commit -am "fix: make electrostatics and summaries ghost aware"`

---

### Task 5: Spin-complete unrestricted/ROHF frontier analysis

**Files:**
- Modify: `src/openwfn/analysis/orbitals.py`
- Modify: `src/openwfn/parsers/gaussian/fchk.py`
- Modify: `src/openwfn/services.py`
- Modify: `src/openwfn/api.py`
- Modify: `src/openwfn/analysis/registry.py`
- Modify: `tests/unit/test_orbitals.py`
- Modify: `tests/parsers/test_gaussian_fchk.py`
- Modify: `tests/integration/test_python_api.py`
- Modify: `tests/unit/test_analysis_registry.py`
- Create: `tests/fixtures/scientific/uhf_beta_homo.fchk`
- Create: `tests/fixtures/scientific/rohf_open_shell.fchk`

**Interfaces:**
- Produces: `OpenWFNCalculation.orbitals(spin: Literal["alpha", "beta", "all"] = "alpha")`.
- Produces: `orbital_frontier(data, spin="alpha"|"beta"|"all")`.
- Produces: registered analysis `frontier-all`; retain existing `frontier` and `beta-frontier`.
- Produces: result field `reference_kind` with restricted/unrestricted classification.
- For `spin="all"`, produces nested alpha/beta frontier data plus `overall_homo_hartree`, `overall_homo_number`, `overall_homo_spin`.

- [ ] **Step 1: Write failing frontier tests**
  - UHF fixture where beta HOMO > alpha HOMO reports beta as overall HOMO in `spin="all"`.
  - Existing explicit alpha and beta calls remain correct.
  - Default alpha result on unrestricted data emits a warning that beta data exist and `spin="all"` is the complete view.
  - ROHF fixture classifies as `restricted_open_shell`; closed-shell water classifies as `restricted_closed_shell`.
  - Frontier selection uses highest-energy occupied and lowest-energy unoccupied candidates rather than array adjacency.
  - All-occupied orbital set raises clear no-LUMO error.
  - Synthesized FCHK occupations expose `occupation_source="electron-count filling"`; unsupported fractional/non-Aufbau source cases are not labeled as independently validated occupations.

- [ ] **Step 2: Run focused tests and confirm failure**
  - Run: `pytest tests/unit/test_orbitals.py tests/parsers/test_gaussian_fchk.py tests/integration/test_python_api.py tests/unit/test_analysis_registry.py -q`

- [ ] **Step 3: Make `frontier_orbitals` occupation/energy aware**
  - Preserve current numbering and eV conversion.

- [ ] **Step 4: Add orbital reference classification and all-spin service result**

- [ ] **Step 5: Extend API and registry compatibly**
  - Keep `frontier` as alpha for backward compatibility but warn when the calculation is unrestricted.
  - Add `frontier-all` instead of changing existing registered result meaning.

- [ ] **Step 6: Re-run focused tests**
  - Expected: PASS.

- [ ] **Step 7: Commit**
  - `git commit -am "fix: report spin complete frontier orbitals"`

---

### Task 6: Batch/CLI spin selection and correct partial propagation

**Files:**
- Modify: `src/openwfn/batch.py`
- Modify: `src/openwfn/cli.py`
- Modify: `tests/integration/test_batch.py`
- Modify: `tests/cli/test_batch_routing.py`
- Modify: `tests/cli/test_commands.py`

**Interfaces:**
- Produces: `run_batch(..., frontier_spin: Literal["alpha", "beta", "all"] = "alpha")` as a keyword-only option.
- Produces: batch CLI `--spin alpha|beta|all` applying to requested `frontier` analysis.
- Configuration fingerprint includes frontier spin choice.

- [ ] **Step 1: Write failing batch tests**
  - One analysis returning `partial` and none returning `failed` yields `BatchRecord.status == "partial"`, not `error`.
  - `success + partial` yields `partial`.
  - Any failed result with at least one success/partial yields `partial`; all failed yields `error`.
  - CLI `batch --analyses frontier --spin all` produces spin-complete frontier data for UHF fixture.
  - Resume fingerprint changes when `--spin` changes.

- [ ] **Step 2: Run focused tests and confirm the all-partial bug**
  - Run: `pytest tests/integration/test_batch.py tests/cli/test_batch_routing.py -q`

- [ ] **Step 3: Replace `_run_one` status aggregation with explicit success/partial/failed logic**
  - `error` only when every requested analysis failed.
  - `partial` whenever at least one analysis is partial or failed and at least one usable result exists.

- [ ] **Step 4: Add batch frontier-spin dispatch and fingerprinting**
  - Preserve existing analysis names in manifest; store spin in configuration metadata/fingerprint.

- [ ] **Step 5: Add CLI `--spin` and route it to `run_batch`**

- [ ] **Step 6: Re-run focused tests**
  - Expected: PASS.

- [ ] **Step 7: Commit**
  - `git commit -am "fix: preserve partial results and spin selection in batch"`

---

### Task 7: Chunked density-grid evaluation

**Files:**
- Modify: `src/openwfn/analysis/grids.py`
- Modify: `src/openwfn/analysis/density.py`
- Modify: `src/openwfn/services.py`
- Modify: `tests/unit/test_density.py`
- Modify: `tests/test_batch_benchmark.py`

**Interfaces:**
- Produces: chunk-capable grid iteration helper yielding ordered point slices without changing final `VolumetricGrid` ordering.
- Produces: `density_grid(..., chunk_size: int = 65536)` internal/service keyword with existing callers retaining defaults.

- [ ] **Step 1: Write failing chunk equivalence tests**
  - Compare chunk sizes 1, 7, and 65536 against current monolithic values on a small grid.
  - Compare integrated electron count within `1e-12` for the same grid.
  - Reject nonpositive chunk size.

- [ ] **Step 2: Run focused tests and confirm failure**
  - Run: `pytest tests/unit/test_density.py tests/test_batch_benchmark.py -q`

- [ ] **Step 3: Implement chunked point generation/evaluation without changing grid ordering**
  - Avoid constructing one full `(n_points, n_basis)` AO matrix.

- [ ] **Step 4: Re-run focused and benchmark-contract tests**
  - Expected: PASS; no benchmark schema change.

- [ ] **Step 5: Commit**
  - `git commit -am "perf: evaluate density grids in chunks"`

---

### Task 8: Documentation, validation registry, and release-facing regression coverage

**Files:**
- Modify: `README.md`
- Modify: `docs/reference/python-api.md`
- Modify: `docs/reference/cli.md`
- Modify: `CHANGELOG.md`
- Modify: `scripts/run_validation.py`
- Modify: validation manifest under existing validation data path if required
- Modify: `tests/docs/*` as needed for reference consistency
- Modify: `tests/integration/test_python_api.py`
- Modify: `tests/cli/test_commands.py`

**Interfaces:**
- No new runtime interface; this task documents exact semantics implemented by Tasks 1-7.

- [ ] **Step 1: Add documentation regression assertions before editing docs**
  - Docs state ECP/ghost effective-charge semantics.
  - Docs state SCF/post-HF density provenance boundary.
  - Docs state conservation `partial` behavior.
  - Docs state unrestricted `spin="all"` / batch `--spin` behavior.
  - Docs state inferred bond heuristic and cube validation meaning.

- [ ] **Step 2: Update scientific validation observations**
  - Keep existing water metrics.
  - Add redistribution-safe minimal regression cases where suitable; do not mark unavailable external references as passed.

- [ ] **Step 3: Update README/API/CLI/CHANGELOG language**
  - Remove universal population `Stable` claims for cases outside validated scope.
  - Document density grid spacing as an accuracy/performance tradeoff rather than blindly changing the 0.15-bohr default.

- [ ] **Step 4: Run docs and validation tests**
  - Run: `pytest tests/docs tests/integration/test_python_api.py tests/cli/test_commands.py -q`
  - Run: `python scripts/run_validation.py`
  - Expected: PASS.

- [ ] **Step 5: Commit**
  - `git commit -am "docs: document scientific correctness boundaries"`

---

### Task 9: Whole-branch verification and compatibility gate

**Files:**
- No planned product-code changes; only fix failures directly attributable to Tasks 1-8.

- [ ] **Step 1: Run formatter/lint checks**
  - Run: `ruff check src tests scripts`
  - Expected: PASS.

- [ ] **Step 2: Run full test suite**
  - Run: `pytest -q`
  - Expected: PASS.

- [ ] **Step 3: Run scientific validation and external repository-only benchmarks**
  - Run: `python scripts/run_validation.py`
  - Run: `python scripts/run_external_benchmarks.py --repository-only`
  - Expected: PASS or documented pending cases only, with no new failures.

- [ ] **Step 4: Build and inspect distributions**
  - Run: `python -m build`
  - Run: `python -m twine check dist/*`
  - Install wheel in a clean environment and smoke-test `openwfn --version`, water summary/frontier/population/density, and Python API import surface.

- [ ] **Step 5: Verify backward-compatible ordinary workflows**
  - Water summary/formula/frontier/population remain within existing numerical tolerances.
  - `calc.orbitals()`, `calc.population()`, `calc.density()`, and current CLI commands still work without new required arguments.

- [ ] **Step 6: Review branch diff against spec**
  - Confirm each spec success criterion has an explicit passing regression test.
  - Confirm no silent scientific fallback remains in the touched paths.

- [ ] **Step 7: Final commit if verification-only adjustments were required**
  - `git commit -am "test: complete scientific correctness regression coverage"`
