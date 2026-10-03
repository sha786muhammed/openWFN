# Vibrational Spectroscopy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add source-faithful Gaussian vibrational parsing, IR/Raman spectrum analysis, normal-mode data, and parity across CLI, Python, MCP, HTML report, guided terminal, and offline Workbench without modifying PR #48.

**Architecture:** Gaussian text output becomes a structure-bearing `CalculationData` whose `records` contains a typed `VibrationalRecord`; basis/orbital/density fields remain absent unless genuinely parsed. Four registered analyses (`vibrations`, `ir-spectrum`, `raman-spectrum`, `normal-mode`) produce the existing `ResultRecord` contract, and every UI layer renders those same results rather than recalculating spectroscopy independently.

**Tech Stack:** Python 3.11+, dataclasses, NumPy, argparse, matplotlib through the existing image-export path, standalone HTML/SVG/JavaScript, 3Dmol.js, pytest, existing MCP SDK.

**Spec:** `docs/superpowers/specs/2026-10-03-vibrational-spectroscopy-design.md`

## Global Constraints

- Keep `MODEL_SCHEMA_VERSION = "2.0"`; use additive typed records through `CalculationData.records`.
- PR #48 / `feat/0.11-hirshfeld-clean` is untouched; all work stays on `feat/0.12-vibrational-spectroscopy`.
- Initial spectroscopy validation status is `Experimental` until independent external evidence supports promotion.
- Preserve source-reported values; missing IR/Raman/vector data are unavailable, never zero-filled.
- Raman activity is not Raman intensity; do not add temperature, laser wavelength, polarization, or instrument corrections.
- Gaussian spectrum broadening default is FWHM = `20.0 cm^-1`, with `sigma = FWHM / (2 * sqrt(2 * ln(2)))`.
- Original stick frequencies/strengths remain present in every spectrum result even when a broadened curve is requested.
- MCP remains read-only and creates no plots/files; REST remains out of scope.
- Existing CLI/API/report/Workbench behavior for non-spectroscopy workflows must remain backward compatible.

## Review Focus

1. **Gaussian logs with multiple geometry/frequency sections:** use the final complete molecular geometry associated with the parsed frequency job; never mix mode vectors with an earlier geometry. Covered in Task 1 parser tests.
2. **Imaginary frequencies:** preserve sign and set `imaginary=True`; never silently absolute-value them. Covered in Tasks 1 and 2.
3. **Partially populated frequency blocks:** absent Raman/IR/vector fields stay unavailable while valid frequency data remain usable. Covered in Tasks 1–3.
4. **Malformed displacement dimensionality:** vectors must match atom count and three Cartesian components or parsing fails explicitly. Covered in Task 1.
5. **Pathological spectrum requests:** nonpositive FWHM, reversed ranges, too few points, or excessive point counts fail before allocation. Covered in Task 2.

---

### Task 1: Typed Vibrational Records and Native Gaussian Frequency Parsing

**Files:**
- Create: `src/openwfn/vibrational.py`
- Modify: `src/openwfn/parsers/gaussian/output.py`
- Modify: `src/openwfn/ingest.py`
- Test: `tests/parsers/test_gaussian_output.py`
- Create fixtures: `tests/fixtures/gaussian/vibrations/`

**Interfaces:**
- Produces: `VibrationalMode`, `VibrationalRecord`, `get_vibrational_record(data: CalculationData) -> VibrationalRecord`.
- Produces: `parse_gaussian_output(path: Path) -> CalculationData | CalculationMetadata`, returning `CalculationData` when enough structure is available and retaining the existing metadata-only fallback for minimal Gaussian logs.
- Record key: `CalculationData.records["vibrations"]`.

- [ ] **Step 1: Write failing typed-record tests** for finite values, one-based mode indices, optional source quantities, imaginary-frequency preservation, atom-count/vector-shape validation, and immutable tuples.

- [ ] **Step 2: Run the focused tests** with `pytest tests/parsers/test_gaussian_output.py -q` and verify failures are due to missing vibrational types/parser behavior.

- [ ] **Step 3: Implement `VibrationalMode` and `VibrationalRecord`** in `src/openwfn/vibrational.py`, including explicit availability properties and `get_vibrational_record` that raises `DataUnavailableError` when the typed record is absent.

- [ ] **Step 4: Add redistribution-safe Gaussian fixtures** covering a nonlinear molecule with IR/Raman/vectors, a linear molecule, an imaginary mode, missing Raman data, and missing vectors. Each fixture must include the exact source lines needed for parser-fidelity assertions.

- [ ] **Step 5: Extend `parse_gaussian_output`** to parse route/method/basis/energy/status as before plus charge/multiplicity, final complete standard/input orientation, frequency blocks, reduced masses, force constants, IR intensities, Raman activities when present, symmetry labels when present, and normal-mode Cartesian displacements when present.

- [ ] **Step 6: Make Gaussian frequency logs normalize as `CalculationData`** through the existing native ingestion path, with molecule/provenance/records populated and basis/orbitals/density left `None`; preserve metadata-only behavior for minimal logs that contain no usable structure.

- [ ] **Step 7: Add parser-fidelity assertions** for exact source values, source order, final-geometry selection, signed imaginary frequency, absent-vs-zero Raman/IR fields, and malformed displacement rejection.

- [ ] **Step 8: Run parser and ingestion tests**: `pytest tests/parsers/test_gaussian_output.py tests/test_ingest.py -q` (or the repository's exact ingestion test path if named differently) and require all passing.

- [ ] **Step 9: Commit** with `git commit -m "feat: parse typed Gaussian vibrational records"`.

---

### Task 2: Capability Gating and Spectroscopy Numerical Analyses

**Files:**
- Create: `src/openwfn/analysis/vibrations.py`
- Create: `src/openwfn/vibrational_services.py`
- Modify: `src/openwfn/capabilities.py`
- Modify: `src/openwfn/analysis/registry.py`
- Test: `tests/unit/test_vibrational_analysis.py`
- Test: `tests/unit/test_capabilities.py`

**Interfaces:**
- Produces: `broaden_lines(frequencies_cm1, strengths, *, fwhm_cm1, frequency_min_cm1, frequency_max_cm1, points) -> tuple[np.ndarray, np.ndarray]`.
- Produces ResultRecord runners: `vibrations(data)`, `ir_spectrum(data, *, fwhm_cm1=20.0, frequency_min_cm1=None, frequency_max_cm1=None, points=None)`, `raman_spectrum(...)`, `normal_mode(data, *, mode: int)`.
- Registry names: `vibrations`, `ir-spectrum`, `raman-spectrum`, `normal-mode`.

- [ ] **Step 1: Write failing analytic broadening tests** asserting peak center, symmetry, half-maximum at FWHM/2, linear superposition, deterministic default grid, and preservation of original stick values.

- [ ] **Step 2: Write failing validation tests** for FWHM `<= 0`, reversed explicit range, `points < 2`, excessive point count, invalid mode index, missing IR, missing Raman, and missing vectors.

- [ ] **Step 3: Run** `pytest tests/unit/test_vibrational_analysis.py tests/unit/test_capabilities.py -q` and verify expected failures.

- [ ] **Step 4: Add inferred capabilities**: `vibrations`, `ir_intensities`, `raman_activities`, and `normal_mode_vectors`, derived exclusively from the typed record contents.

- [ ] **Step 5: Implement bounded Gaussian broadening** with the approved sigma/FWHM relationship, deterministic margins, finite-input checks, and a hard point-count ceiling chosen alongside an explicit test.

- [ ] **Step 6: Implement the four ResultRecord services** with `Experimental` validation status, explicit units, original source lines/sticks, broadened arrays for spectra, signed imaginary-mode metadata, and clear DataUnavailable/ValueError failures.

- [ ] **Step 7: Register all four analyses** with capability requirements in `analysis/registry.py` so generic Python, batch, report, and MCP paths discover them automatically.

- [ ] **Step 8: Run focused analysis/registry tests** and require all passing.

- [ ] **Step 9: Commit** with `git commit -m "feat: add vibrational and spectrum analyses"`.

---

### Task 3: Python API, MCP, and Cross-Surface Numerical Parity

**Files:**
- Modify: `src/openwfn/api.py`
- Test: `tests/test_api.py` or existing API test module
- Test: `tests/test_mcp_server.py` or existing MCP test module
- Create: `tests/integration/test_vibrational_parity.py`

**Interfaces:**
- Generic API remains authoritative: `calc.analyze("vibrations")`, `calc.analyze("ir-spectrum", ...)`, `calc.analyze("raman-spectrum", ...)`, `calc.analyze("normal-mode", mode=...)`.
- Optional convenience wrappers are thin calls to `run_analysis_safe` only.
- MCP continues to expose analyses exclusively through existing `list_analyses()` and `run_analysis()`.

- [ ] **Step 1: Write failing API tests** proving the four analyses return the expected `ResultRecord` fields and parameters without alternate calculations.

- [ ] **Step 2: Write failing MCP tests** proving `list_analyses()` includes the four names and `run_analysis()` returns byte-for-byte-equivalent scientific `data`, `units`, status, warnings, and provenance to Python for the same input/parameters.

- [ ] **Step 3: Implement thin API convenience methods only if they materially improve usability** (`vibrations`, `ir_spectrum`, `raman_spectrum`, `normal_mode`); otherwise preserve generic `analyze` as the only new Python surface.

- [ ] **Step 4: Confirm MCP needs no spectroscopy-specific code** beyond registry discovery; if a parameter-passing limitation exists in the current MCP signature, extend `run_analysis` with a bounded JSON-compatible `parameters` mapping rather than adding separate MCP tools.

- [ ] **Step 5: Run API/MCP/parity tests** and require identical numerical results.

- [ ] **Step 6: Commit** with `git commit -m "test: enforce spectroscopy API and MCP parity"`.

---

### Task 4: CLI, Row-Oriented CSV, Plot Export, and Guided Terminal

**Files:**
- Modify: `src/openwfn/cli.py`
- Modify: `src/openwfn/presentation.py`
- Modify: `src/openwfn/exporters/tables.py`
- Modify: `src/openwfn/exporters/images.py`
- Modify: `src/openwfn/interactive.py`
- Modify: `src/openwfn/palette.py`
- Test: `tests/test_cli.py` or existing CLI test modules
- Test: `tests/unit/test_exporters.py`
- Test: guided-interface test module if present

**Interfaces:**
- CLI: `openwfn FILE vibrations`, `openwfn FILE vibrations mode N`, `openwfn FILE spectra ir`, `openwfn FILE spectra raman`.
- Spectrum parameters: `--fwhm`, `--min`, `--max`, `--points` mapped directly to the registered analysis parameters.
- Export: row-oriented mode/spectrum CSV; PNG/SVG plot uses the same ResultRecord arrays.
- Guided workflow label: `Analyze vibrations and spectra`.

- [ ] **Step 1: Write failing CLI tests** for human table output, JSON completeness, long-array abbreviation, missing-data errors, mode selection, and spectroscopy command routing.

- [ ] **Step 2: Write failing CSV tests** asserting one row per mode or spectrum point with explicit headers/units instead of Python-list cells.

- [ ] **Step 3: Write failing PNG/SVG exporter tests** asserting valid files, requested DPI for PNG, axis labels `Wavenumber (cm^-1)`, correct IR vs Raman y-labels, and unchanged numerical input arrays.

- [ ] **Step 4: Implement specialized human rendering** for `vibrational_modes` and spectrum summaries while retaining the existing deterministic, non-Rich presentation style and standard status/warning footer.

- [ ] **Step 5: Implement CLI parser/routing and exports** with no duplicated spectroscopy calculations outside the registry/services.

- [ ] **Step 6: Extend the guided palette** with spectroscopy routing and choices for mode table, IR, Raman, and single-mode inspection; results still pass through the shared renderer.

- [ ] **Step 7: Run CLI/export/guided tests** and require all passing.

- [ ] **Step 8: Commit** with `git commit -m "feat: expose vibrational spectroscopy in terminal workflows"`.

---

### Task 5: Spectroscopy-Specific HTML Research Report Rendering

**Files:**
- Modify: `src/openwfn/reporting.py`
- Test: `tests/test_reporting.py` or existing report test module
- Test: `tests/integration/test_vibrational_report.py`

**Interfaces:**
- Report still consumes `run_analysis_safe` results.
- `vibrations` renders a mode table.
- `ir-spectrum` and `raman-spectrum` render self-contained inline SVG curves plus stick/peak tables.
- Embedded `#openwfn-report` JSON remains the authoritative machine-readable payload.

- [ ] **Step 1: Write failing HTML tests** for mode-table columns, IR SVG, Raman SVG, correct labels/units, warnings/status, and absence of external network assets.

- [ ] **Step 2: Write parity assertion** that values encoded in the report JSON exactly match Python API ResultRecord values for the same parameters.

- [ ] **Step 3: Add spectroscopy-specific report renderers** that consume existing section ResultRecords and do not recalculate spectra.

- [ ] **Step 4: Keep generic key/value rendering unchanged** for all existing analyses.

- [ ] **Step 5: Run report tests** and require valid standalone HTML with spectroscopy sections.

- [ ] **Step 6: Commit** with `git commit -m "feat: render vibrational spectra in research reports"`.

---

### Task 6: Offline Workbench Vibrations Workspace and Normal-Mode Visualization

**Files:**
- Modify: `src/openwfn/workbench/payload.py`
- Modify: `src/openwfn/workbench/export.py`
- Test: `tests/integration/test_workbench_export.py`
- Test: `tests/integration/test_workbench_contract.py`
- Test: `tests/test_workbench_javascript.py`
- Modify browser validation script if needed: `scripts/validate_workbench_browser.py`

**Interfaces:**
- Workbench payload gains spectroscopy data derived from the same registered results; bump Workbench payload schema version only if required by the serialized contract.
- Add one top-level `Vibrations` workspace containing mode table/selector, mode details, IR/Raman panels, and 3D displacement visualization.
- Visualization amplitude is UI-only and never feeds back into scientific values.

- [ ] **Step 1: Write failing payload tests** proving embedded mode/spectrum values equal registry outputs and missing vectors produce an explicit unavailable state.

- [ ] **Step 2: Write failing DOM/JavaScript contract tests** for the new Vibrations workspace, mode selection, IR/Raman panels, amplitude control, and displacement vector data.

- [ ] **Step 3: Extend `WorkbenchPayload.from_calculation`** to attach spectroscopy properties only when a vibrational record exists; do not add expensive or unrelated field calculations for spectroscopy-only logs.

- [ ] **Step 4: Extend the current dark Workbench HTML/JS** with the Vibrations workspace while preserving Structure/Orbitals/Density/ESP/Measurements behavior and responsive breakpoints.

- [ ] **Step 5: Render source displacement arrows/vectors** mapped by atom order; when vectors are unavailable, show a clear message and no invented animation.

- [ ] **Step 6: Render IR/Raman SVG/canvas panels from embedded ResultRecord arrays** and make selected spectral sticks/mode rows update the same selected-mode state.

- [ ] **Step 7: Run Node/browser/workbench tests** plus the documented Chromium validation where available.

- [ ] **Step 8: Commit** with `git commit -m "feat: add vibrations to offline workbench"`.

---

### Task 7: Validation Corpus, Documentation, Resource Checks, and Release Boundary

**Files:**
- Create: `docs/science/vibrational-spectroscopy.md`
- Modify: `docs/reference/cli.md`
- Modify: `docs/reference/python-api.md`
- Modify: `docs/mcp.md`
- Modify: `docs/workbench.md`
- Modify: `docs/project/everyday-qc-validation.md`
- Modify: `ROADMAP.md`
- Modify: `validation/manifest.json`
- Create validation evidence under: `validation/vibrational-spectroscopy/`
- Modify: `scripts/benchmark_resources.py`
- Modify relevant CI/release workflow only if the new benchmark is intentionally made a release gate

**Interfaces:**
- Documentation names status `Experimental` and distinguishes source quantities from derived broadened curves.
- Validation evidence records parser fidelity and analytic broadening separately from any future independent external-reference promotion gate.

- [ ] **Step 1: Add a reproducible validation script/report** that records fixture hashes, parsed source values, analytic Gaussian checks, tolerances, openWFN version/commit, and pass/fail status.

- [ ] **Step 2: Add resource-benchmark spectroscopy workflows** using a small real frequency fixture: mode table, IR spectrum, Raman spectrum, HTML report, and Workbench; preserve bounded runtime/RSS/output-size checks.

- [ ] **Step 3: Write scientific documentation** covering harmonic modes, imaginary-frequency convention, source vs derived data, IR units, Raman activity vs intensity, broadening/FWHM, limitations, and validation scope.

- [ ] **Step 4: Update CLI/Python/MCP/Workbench docs and roadmap** with exact commands and status boundaries; do not claim REST support or `Validated` status.

- [ ] **Step 5: Update `validation/manifest.json`** so spectroscopy is authoritative as `Experimental` with links to its evidence and documented unsupported/missing-data boundaries.

- [ ] **Step 6: Run the full repository verification suite**:
  - `python -m pytest -q`
  - `python -m ruff check src tests scripts`
  - `python scripts/run_validation.py`
  - `python scripts/run_interop_validation.py`
  - `python scripts/check_repository.py --root .`
  - `python scripts/check_docs.py --root .`
  - `python -m mkdocs build --strict`
  - `python scripts/benchmark_resources.py --output resource-report.json`

- [ ] **Step 7: Verify PR #48 head SHA is unchanged** from the value recorded before this branch was created and compare this branch only against `main`.

- [ ] **Step 8: Commit** with `git commit -m "docs: validate vibrational spectroscopy workflow"`.

---

### Task 8: Final Branch Verification and Review-Ready PR

**Files:**
- No scientific code changes unless verification finds a defect.
- Create/update release note only if the repository's normal feature-PR policy requires one before review.

**Interfaces:**
- The branch must be independently reviewable from `main` and must not depend on unmerged Hirshfeld PR code.

- [ ] **Step 1: Re-run the complete verification suite from Task 7 on the final branch head.**

- [ ] **Step 2: Inspect `git diff main...feat/0.12-vibrational-spectroscopy`** for accidental Hirshfeld/PR #48 changes, generated junk, secrets, machine paths, or unsupported validation claims.

- [ ] **Step 3: Confirm four-way scientific parity** for one real Gaussian fixture: Python API == CLI JSON == MCP == embedded report JSON for `vibrations`, `ir-spectrum`, `raman-spectrum`, and `normal-mode`.

- [ ] **Step 4: Confirm UI derivation**: HTML and Workbench values originate from the same ResultRecords and visualization amplitude/broadening controls do not mutate source data.

- [ ] **Step 5: Open a separate draft PR against `main`** titled `feat: vibrational spectroscopy and normal modes`, including scientific scope, validation boundary, exact tests run, limitations, and an explicit note that PR #48 is independent and untouched.
