# Scientific Correctness Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate silent scientific-correctness failures in openWFN 0.8.0 for ECP/ghost atoms, population and density conservation, post-HF density provenance, unrestricted/ROHF frontiers, cube validation, warning propagation, and batch status handling while preserving current public workflows.

**Architecture:** Extend the existing typed model with source-faithful nuclear-charge and density-source metadata, centralize scientific expectations/validation in `src/openwfn/scientific.py`, and propagate evidence-based status/warnings through services, registry, Python API, CLI, and batch. Keep existing public method names and result fields where possible; add metadata rather than silently guessing.

**Tech Stack:** Python 3.10+, NumPy, pytest, argparse CLI, current `ResultRecord`/registry/batch architecture.

**Spec:** `docs/superpowers/specs/2026-09-28-scientific-correctness-hardening-design.md`

## Global Constraints

- Preserve existing public calls such as `openwfn.load`, `calc.orbitals`, `calc.population`, `calc.density`, registered analyses, and current CLI command families.
- Keep `RESULT_SCHEMA_VERSION` and `BATCH_SCHEMA_VERSION` readable by existing 0.8.0 consumers unless a schema break becomes unavoidable.
- Use FCHK source records as authoritative where available; fallbacks must be explicit and warned.
- Scientific consistency failures with useful numbers return `status="partial"`; informational provenance warnings may remain `success`.
- Population conservation tolerance: `1e-6 e`.
- Density relative validation tolerance for nonzero targets: `5e-3`.
- Zero-target spin-density absolute tolerance: `5e-3 e`.
- Ghost nuclear-charge tolerance: `1e-12`.
- Löwdin warning threshold: smallest positive overlap eigenvalue `< 1e-8` or condition number `> 1e10`.
- Do not claim post-SCF density support until a real post-SCF density record is parsed and selected.
- Keep water/benzene behavior numerically unchanged within current tolerances.

## Review Focus

- Missing `Nuclear charges`: fall back deterministically and warn; Task 1.
- Fractional/non-Aufbau occupations: expose synthesized occupation provenance and do not silently claim support; Task 5.
- All orbitals occupied: fail clearly because LUMO is unavailable; Task 5.
- All analysis results are `partial`: batch record must remain `partial`, retain usable result data, and never become `error`; Task 6.
- API convenience methods must merge source warnings with analysis warnings rather than overwrite them; Task 2.
- Chunk boundaries must not alter density values or integrals; Task 7.

---

### Task 1: Source-faithful scientific metadata

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
- `Atom.nuclear_charge: float | None = None`, preserving `Atom(atomic_number, coordinates)`.
- `DensityMatrix.source: str | None = None`; parsed SCF density uses `source="scf"`.
- `effective_nuclear_charge(atom: Atom) -> float`.
- `is_ghost_atom(atom: Atom, tolerance: float = 1e-12) -> bool`.
- `ElectronExpectation(value: float, source: str, warnings: tuple[str, ...])`.
- `expected_electron_count(data: CalculationData, kind: str) -> ElectronExpectation`.
- `orbital_reference_kind(data: CalculationData) -> Literal["restricted_closed_shell", "restricted_open_shell", "unrestricted", "unknown"]`.
- `is_post_hf_method(method: str | None) -> bool` using explicit MPn/CC/QCI/CI family matching, not broad substring guesses.

- [ ] **Step 1: Write failing parser/model tests**
  - ECP Si: atomic number 14, nuclear charge 4.
  - Ghost O: atomic number 8, nuclear charge 0.
  - Missing `Nuclear charges`: `None` plus provenance fallback warning.
  - `Number of electrons` wins over reconstructed counts.
  - Alpha/beta/spin expectations use FCHK electron records.
  - Parsed SCF density has `source="scf"`.

- [ ] **Step 2: Run tests and verify failure**
  - `pytest tests/unit/test_model.py tests/parsers/test_gaussian_fchk.py -q`

- [ ] **Step 3: Add optional model fields with finite-value validation**

- [ ] **Step 4: Parse `Nuclear charges`; validate length equals atom count**

- [ ] **Step 5: Implement `scientific.py` helpers**
  - Total expectation precedence: FCHK `Number of electrons` -> effective charges minus molecular charge -> atomic-number fallback with warning.
  - Zero spin expectation is valid.

- [ ] **Step 6: Re-run focused tests; expect PASS**

- [ ] **Step 7: Commit**
  - `git commit -am "fix: preserve source nuclear charges and electron metadata"`

---

### Task 2: Population correctness, Löwdin diagnostics, and warning propagation

**Files:**
- Modify: `src/openwfn/analysis/population.py`
- Modify: `src/openwfn/services.py`
- Modify: `src/openwfn/api.py`
- Modify: `tests/unit/test_population.py`
- Modify: `tests/integration/test_python_api.py`

**Interfaces:**
- Population charges consume effective nuclear charges from Task 1.
- Population result data adds `density_source`, and Löwdin adds `overlap_min_eigenvalue` and `overlap_condition_number`.
- `OpenWFNCalculation._with_provenance(result)` merges `result.warnings` with source warnings, preserving order and removing duplicates.

- [ ] **Step 1: Write failing regression tests**
  - ECP/ghost atomic charges use effective nuclear charge.
  - `conservation_error > 1e-6` -> values retained, `status="partial"`, `validation_status="Experimental"`, warning includes observed error/tolerance.
  - Consistent population remains `success`.
  - Near-linear Löwdin overlap -> `partial` + diagnostic warning.
  - Post-HF fixture using SCF density reports `density_source="scf"` and warning.
  - High-level `calc.population()` preserves both analysis warnings and parser/source warnings.

- [ ] **Step 2: Run tests and verify failure**
  - `pytest tests/unit/test_population.py tests/integration/test_python_api.py -q`

- [ ] **Step 3: Replace atomic-number charge subtraction with effective nuclear charges**
  - Keep low-level public signatures unchanged.

- [ ] **Step 4: Add conservation and Löwdin-condition status logic in service layer**

- [ ] **Step 5: Fix `_with_provenance` to merge rather than replace warnings**

- [ ] **Step 6: Re-run focused tests; expect PASS**

- [ ] **Step 7: Commit**
  - `git commit -am "fix: enforce population consistency and warning propagation"`

---

### Task 3: Density validation and evidence-based cube status

**Files:**
- Modify: `src/openwfn/analysis/density.py`
- Modify: `src/openwfn/services.py`
- Modify: `tests/unit/test_density.py`
- Modify: `tests/cli/test_commands.py`

**Interfaces:**
- Extend `IntegrationResult` with `absolute_error: float`, `relative_error: float | None`, `error_metric: Literal["absolute", "relative"]`, `passed: bool`.
- Keep existing `integrate_density(grid, expected_electrons, ...)` call form; optional keyword tolerances may be added without breaking two-argument callers.
- Density/cube result data adds `expectation_source`, `density_source`, `absolute_error`, `error_metric`, and nullable `relative_error`.

- [ ] **Step 1: Write failing tests**
  - Closed-shell singlet spin target 0 uses absolute error and succeeds near zero.
  - Nonzero total/alpha/beta uses relative error.
  - Bad density integration returns `partial`/`Experimental` with warning rather than clean validated success.
  - Post-HF SCF density names its source and warns.

- [ ] **Step 2: Run tests and verify failure**
  - `pytest tests/unit/test_density.py tests/cli/test_commands.py -q`

- [ ] **Step 3: Implement zero-target-aware `integrate_density`**
  - If `abs(expected) <= 1e-12`, use absolute error with `5e-3 e` tolerance; otherwise relative error with `5e-3` tolerance.

- [ ] **Step 4: Replace service `_expected_electrons` with Task 1 helper and propagate warnings**

- [ ] **Step 5: Make `density_cube_export` validate the exact generated grid before assigning `Validated`**
  - Failed validation still writes requested cube but returns `partial`/`Experimental`.

- [ ] **Step 6: Re-run focused tests; expect PASS**

- [ ] **Step 7: Commit**
  - `git commit -am "fix: validate density and cube electron conservation"`

---

### Task 4: ECP/ghost-safe ESP, cube headers, and summaries

**Files:**
- Modify: `src/openwfn/analysis/electrostatics.py`
- Modify: `src/openwfn/exporters/cube.py`
- Modify: `src/openwfn/services.py`
- Modify: `tests/unit/test_electrostatics.py`
- Modify: `tests/parsers/test_gaussian_cube.py`
- Modify: `tests/unit/test_analysis_registry.py`

**Interfaces:**
- Summary adds `centers`, `physical_nuclei`, `ghost_centers`, `bond_source`; existing fields remain.

- [ ] **Step 1: Write failing tests**
  - ECP nuclear ESP uses 4 rather than 14.
  - Ghost nuclear ESP contribution is zero.
  - Cube atom line preserves atomic-number identity but uses effective nuclear charge in charge column.
  - Ghost summary excludes ghost from formula, COM, inferred bonds, and physical fragments while retaining center count.
  - Water summary remains numerically unchanged and states `bond_source="covalent-radius heuristic"`.

- [ ] **Step 2: Run tests and verify failure**
  - `pytest tests/unit/test_electrostatics.py tests/parsers/test_gaussian_cube.py tests/unit/test_analysis_registry.py -q`

- [ ] **Step 3: Use effective charges in ESP/cube serialization**

- [ ] **Step 4: Make molecular summary ghost-aware with index remapping for physical bonds/fragments**
  - Ghost filtering warning is informational, not automatically `partial`.

- [ ] **Step 5: Re-run focused tests; expect PASS**

- [ ] **Step 6: Commit**
  - `git commit -am "fix: make electrostatics and summaries ghost aware"`

---

### Task 5: Spin-complete UHF/ROHF frontier handling

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
- `OpenWFNCalculation.orbitals(spin: Literal["alpha", "beta", "all"] = "alpha")`.
- `orbital_frontier(data, spin="alpha"|"beta"|"all")`.
- Add registered `frontier-all`; retain `frontier` and `beta-frontier`.
- Result data adds `reference_kind` and `occupation_source`.
- `spin="all"` returns alpha/beta frontier payloads plus `overall_homo_hartree`, `overall_homo_number`, `overall_homo_spin`.

- [ ] **Step 1: Write failing tests**
  - UHF fixture with beta HOMO above alpha reports beta overall HOMO.
  - Explicit alpha/beta paths remain correct.
  - Default alpha on UHF warns that beta exists and `all` is complete view.
  - ROHF -> `restricted_open_shell`; water -> `restricted_closed_shell`.
  - HOMO is highest-energy occupied; LUMO is lowest-energy unoccupied, not blindly `homo_index + 1`.
  - All occupied -> clear no-LUMO error.
  - FCHK synthesized occupations expose `occupation_source="electron-count filling"`; anomalous/non-Aufbau ordering produces warning rather than silent ordinary-gap interpretation.

- [ ] **Step 2: Run tests and verify failure**
  - `pytest tests/unit/test_orbitals.py tests/parsers/test_gaussian_fchk.py tests/integration/test_python_api.py tests/unit/test_analysis_registry.py -q`

- [ ] **Step 3: Make frontier selection occupation/energy aware**

- [ ] **Step 4: Add reference classification and all-spin service result**

- [ ] **Step 5: Extend API/registry compatibly; merge warnings via Task 2 behavior**

- [ ] **Step 6: Re-run focused tests; expect PASS**

- [ ] **Step 7: Commit**
  - `git commit -am "fix: report spin complete frontier orbitals"`

---

### Task 6: Batch/CLI spin selection and partial-result preservation

**Files:**
- Modify: `src/openwfn/batch.py`
- Modify: `src/openwfn/cli.py`
- Modify: `tests/integration/test_batch.py`
- Modify: `tests/cli/test_batch_routing.py`
- Modify: `tests/cli/test_commands.py`

**Interfaces:**
- Add keyword-only `frontier_spin: Literal["alpha", "beta", "all"] = "alpha"` to `run_batch`.
- Add batch CLI `--spin alpha|beta|all` applying to requested `frontier` analysis.
- Include frontier spin in configuration fingerprint.

- [ ] **Step 1: Write failing status tests**
  - One/all `partial` results -> batch record `partial`, never `error`.
  - `success + partial` -> `partial`.
  - `success/partial + failed` -> `partial`; all failed -> `error`.
  - All-partial record retains first usable partial `.data` in `BatchRecord.result`.
  - CSV index counts partial analyses explicitly or otherwise does not mislabel them as failures.

- [ ] **Step 2: Write failing spin-routing tests**
  - `batch --analyses frontier --spin all` returns spin-complete UHF result.
  - Resume fingerprint changes when spin changes.

- [ ] **Step 3: Run focused tests and confirm current all-partial bug**
  - `pytest tests/integration/test_batch.py tests/cli/test_batch_routing.py -q`

- [ ] **Step 4: Fix `_run_one` aggregation and usable-result selection**
  - `error` only when every requested analysis failed.

- [ ] **Step 5: Add spin dispatch/fingerprinting and CLI option**

- [ ] **Step 6: Re-run focused tests; expect PASS**

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
- Add ordered grid-point chunk iterator/helper.
- Add internal/service `density_grid(..., chunk_size: int = 65536)` keyword; existing callers need no change.

- [ ] **Step 1: Write failing chunk-equivalence tests**
  - Chunk sizes 1, 7, 65536 match monolithic values and integral within `1e-12` on a small grid.
  - Reject nonpositive chunk size.

- [ ] **Step 2: Run tests and verify failure**
  - `pytest tests/unit/test_density.py tests/test_batch_benchmark.py -q`

- [ ] **Step 3: Implement chunked point generation/evaluation preserving C-order grid layout**
  - Avoid one monolithic `(n_points, n_basis)` AO matrix.

- [ ] **Step 4: Re-run focused tests; expect PASS**

- [ ] **Step 5: Commit**
  - `git commit -am "perf: evaluate density grids in chunks"`

---

### Task 8: Documentation and permanent regression/validation coverage

**Files:**
- Modify: `README.md`
- Modify: `docs/reference/python-api.md`
- Modify: `docs/reference/cli.md`
- Modify: `CHANGELOG.md`
- Modify: `scripts/run_validation.py`
- Modify existing validation manifest if appropriate
- Modify relevant `tests/docs/*`

- [ ] **Step 1: Add docs regression assertions before edits**
  - ECP/ghost effective charges.
  - authoritative electron-count/fallback behavior.
  - conservation partial status.
  - SCF/post-HF density provenance.
  - UHF/ROHF and `spin="all"`/batch `--spin` semantics.
  - evidence-based cube validation and inferred-bond heuristic.

- [ ] **Step 2: Update validation registry with redistribution-safe regression cases where appropriate**
  - Keep unavailable external references pending rather than claiming validation.

- [ ] **Step 3: Update README/API/CLI/CHANGELOG**
  - Remove universal population `Stable` claims outside tested scope.
  - Document 0.15-bohr grid spacing as accuracy/performance tradeoff rather than changing it blindly.

- [ ] **Step 4: Run docs/validation tests**
  - `pytest tests/docs tests/integration/test_python_api.py tests/cli/test_commands.py -q`
  - `python scripts/run_validation.py`

- [ ] **Step 5: Commit**
  - `git commit -am "docs: document scientific correctness boundaries"`

---

### Task 9: Whole-branch verification gate

**Files:** No planned product changes except direct fixes for verification failures attributable to Tasks 1-8.

- [ ] **Step 1: Lint**
  - `ruff check src tests scripts`

- [ ] **Step 2: Full tests**
  - `pytest -q`

- [ ] **Step 3: Scientific validation**
  - `python scripts/run_validation.py`
  - `python scripts/run_external_benchmarks.py --repository-only`

- [ ] **Step 4: Distribution checks**
  - `python -m build`
  - `python -m twine check dist/*`
  - Install wheel in a clean environment and smoke-test `openwfn --version`, water summary/frontier/population/density, batch, and Python API imports.

- [ ] **Step 5: Backward-compatibility check**
  - Water/benzene ordinary workflows retain current numerical results within existing tolerances.
  - Existing API/CLI calls work without new required arguments.
  - JSON/result schema remains readable.

- [ ] **Step 6: Spec coverage review**
  - Every spec success criterion must point to a passing regression test.
  - No touched scientific fallback may remain silent.

- [ ] **Step 7: Final verification commit only if needed**
  - `git commit -am "test: complete scientific correctness regression coverage"`
