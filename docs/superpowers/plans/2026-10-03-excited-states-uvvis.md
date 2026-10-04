# Excited States and UV–Vis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a method-general, source-faithful excited-state and UV–Vis subsystem for Gaussian, ORCA, and Q-Chem that can represent all parser-detectable method families without conflating incompatible amplitude conventions.

**Architecture:** Three source adapters normalize program-specific text into one typed `ExcitedStateCollection` with explicit one-based job blocks, states, contributions, and convention-labelled amplitude blocks. Registered analyses consume that model once; CLI, Python, MCP, CSV/JSON/plots, HTML reports, and Workbench render the same `ResultRecord` data.

**Tech Stack:** Python 3.10+, dataclasses, NumPy, existing `CalculationData.records`, analysis registry/`ResultRecord`, shared spectrum utilities from the PR #49 baseline, matplotlib exporters, standalone HTML/SVG/JavaScript, pytest, optional IOData/cclib only as ingestion/evidence helpers.

**Spec:** `docs/superpowers/specs/2026-10-03-excited-states-uvvis-design.md`

## Global Constraints

- Initial scientific status is `Experimental`; later validation may promote narrower components only.
- Preserve source-reported energies, oscillator strengths, transition dipoles, labels, contributions, amplitudes, and diagnostics. Never invent missing values.
- TDDFT/RPA X/Y, CIS/CI, ADC, EOM left/right, spin-flip, multireference, and unknown coefficients remain explicitly different conventions.
- Source jobs remain separate. Never mix excited-state data from one job with geometry, charge, multiplicity, method, or reference metadata from another.
- Public `job` and `state` selectors are one-based.
- A positive excitation energy may expose a derived wavelength. Zero/nonpositive energies remain representable but are ineligible for wavelength-domain spectrum points.
- UV–Vis uses source oscillator strength only. Missing strength is unavailable, not zero. A true `f=0` value remains a valid dark line. A negative source oscillator strength is preserved in source data but excluded from the simulated curve with an explicit warning; never clamp it to zero.
- Default UV–Vis broadening is a Gaussian in **energy space** with `FWHM = 0.20 eV`. This is a deterministic visualization/post-processing default, not an experimental linewidth.
- Continuous energy→wavelength conversion applies the absolute Jacobian. Never relabel an evenly spaced energy curve as wavelength.
- Do not call the simulated curve experimental absorbance or molar extinction.
- Bound state counts, amplitude counts, spectrum points, and parser buffers before allocation.
- REST is out of scope.
- PR #48 and PR #49 branches remain untouched by implementation commits.
- **Dependency gate:** before production implementation, either PR #49 is merged into `main` and this branch is rebased onto that baseline, or the user explicitly approves stacking this branch on PR #49. Do not duplicate PR #49’s generic MCP parameter forwarding, spectrum-export plumbing, or report/Workbench infrastructure.
- Do not publish a release or change stable version metadata.

## Review Focus

1. **Multi-job outputs:** repeated state/root numbers in different jobs must remain distinct and require explicit `job` selection when ambiguous. Covered in Tasks 1–4 and 6.
2. **Dark/invalid optical states:** `f=0` is retained; missing or negative `f` and nonpositive energies are excluded from curves with reasons, never rewritten. Covered in Task 6.
3. **Percentages versus amplitudes:** printed transition percentages/weights must never become NTO-ready coefficients. Covered in Tasks 1 and 5.
4. **Method aliases/unknown methods:** aliases map to canonical families while exact source labels survive; unknown methods still produce generic state records. Covered in Task 5.
5. **Huge outputs:** hard state/amplitude/curve limits fail before unbounded allocation. Covered in Tasks 1–4 and 6.

---

### Task 1: Universal Model, Job Blocks, and Capabilities

**Files:**
- Create: `src/openwfn/excited_states.py`
- Modify: `src/openwfn/capabilities.py`
- Modify: `src/openwfn/data.py` only if the rebased PR #49 baseline still needs a shared structure→minimal-calculation helper
- Test: `tests/unit/test_excited_state_model.py`
- Test: `tests/unit/test_capabilities.py`

**Interfaces:**
- Produces frozen dataclasses: `TransitionContribution`, `AmplitudeBlock`, `ExcitedState`, `ExcitedStateJob`, `ExcitedStateCollection`.
- Produces: `get_excited_state_collection(data: CalculationData | OpenWFNData) -> ExcitedStateCollection`.
- Record key: `CalculationData.records["excited_states"]`.
- Capability names: `excited_states`, `optical_oscillator_strengths`, `transition_dipoles`, `excitation_contributions`, `excitation_amplitudes`, `nto_ready_amplitudes`.
- Constants: `MAX_EXCITED_STATES_PER_JOB = 10000`, `MAX_AMPLITUDES_PER_STATE = 1000000`.

- [ ] **Step 1: Write failing model tests** for one-based job/state indices, finite excitation energy, optional source numbering, unavailable-vs-zero optical fields, immutable tuples, repeated source root numbers across jobs, and wavelength only for positive energy.
- [ ] **Step 2: Write failing semantic tests** proving a percent/weight contribution is not an amplitude, unknown amplitude conventions remain representable but are not NTO-ready, and multi-job records require per-job metadata.
- [ ] **Step 3: Write failing limit tests** proving the two hard limits reject oversized payloads before materialization.
- [ ] **Step 4: Run** `pytest tests/unit/test_excited_state_model.py tests/unit/test_capabilities.py -q` and confirm RED failures come from missing types/capabilities.
- [ ] **Step 5: Implement the dataclasses and accessor** in `src/openwfn/excited_states.py` with exact source labels preserved separately from canonical method family.
- [ ] **Step 6: Add capability inference** from typed-record contents only; `nto_ready_amplitudes` must consult Task 5’s semantics registry.
- [ ] **Step 7: Re-run focused tests** and require PASS.
- [ ] **Step 8: Commit** `feat: add typed excited-state records`.

---

### Task 2: Gaussian Adapter

**Files:**
- Create: `src/openwfn/parsers/excited/__init__.py`
- Create: `src/openwfn/parsers/excited/gaussian.py`
- Modify: `src/openwfn/parsers/gaussian/output.py`
- Modify: `src/openwfn/ingest.py`
- Create: `tests/fixtures/gaussian/excited/`
- Create: `tests/parsers/test_gaussian_excited_states.py`

**Interfaces:**
- Produces: `parse_gaussian_excited_states(text: str) -> ExcitedStateCollection | None`.
- Native Gaussian ingestion attaches the typed collection to the correct calculation/job record without replacing existing vibrational or other records.

- [ ] **Step 1: Add redistribution-safe fixtures** for TDDFT/TDA/CIS-like states, singlet/triplet labels, dark state, oscillator strengths, transition dipoles when printed, dominant transitions, spin-flip/core examples when available, and a multi-Link job followed by unrelated metadata.
- [ ] **Step 2: Write failing fidelity tests** for exact energies, oscillator strengths, labels, multiplicity/symmetry, source order, contribution quantity/convention, and exact Link/job association.
- [ ] **Step 3: Write failing malformed/limit tests** for incomplete state lines, nonfinite numerics, mismatched transitions, repeated roots across jobs, and oversized blocks.
- [ ] **Step 4: Run** `pytest tests/parsers/test_gaussian_excited_states.py -q` and verify RED.
- [ ] **Step 5: Implement conservative job splitting and parsing**; only create amplitude blocks when the printed convention is explicit.
- [ ] **Step 6: Attach records through Gaussian ingestion** and add a Link1 regression proving later metadata cannot overwrite the excited-state job context.
- [ ] **Step 7: Run Gaussian parser plus existing Gaussian regression suites** and require PASS.
- [ ] **Step 8: Commit** `feat: parse Gaussian excited states`.

---

### Task 3: ORCA Adapter

**Files:**
- Create: `src/openwfn/parsers/excited/orca.py`
- Modify: `src/openwfn/ingest.py`
- Modify: `src/openwfn/adapters/iodata.py` only if needed for shared augmentation of a structure-bearing calculation
- Create: `tests/fixtures/orca/excited/`
- Create: `tests/parsers/test_orca_excited_states.py`

**Interfaces:**
- Produces: `parse_orca_excited_states(text: str) -> ExcitedStateCollection | None`.
- ORCA keeps the existing IOData structure/wavefunction path; the native excited-state adapter augments it.

- [ ] **Step 1: Add project-owned ORCA excerpts** covering representative labels for TDDFT/TDA/CIS, ROCIS/spin-flip, ADC/CVS, EOM/STEOM, local/PNO excited-state methods, CASSCF/multireference states, and a generic unknown-method state block where source grammar permits.
- [ ] **Step 2: Write failing fidelity tests** for exact energies, oscillator strengths, transition moments, root numbering, multiplicity/spin, method text, diagnostics, and contribution/amplitude convention tags.
- [ ] **Step 3: Write failing fallback tests** showing parseable unknown-method states become `method_family="other"` with no invented optical/amplitude fields.
- [ ] **Step 4: Write failing multi-job/limit tests** for repeated roots and oversized blocks.
- [ ] **Step 5: Run** `pytest tests/parsers/test_orca_excited_states.py -q` and verify RED.
- [ ] **Step 6: Implement the adapter and ingestion augmentation**; reuse IOData structure/provenance when trustworthy and create only a minimal structure-bearing `CalculationData` when necessary to host records.
- [ ] **Step 7: Run ORCA parser, interoperability, and output-property regression suites** and require PASS.
- [ ] **Step 8: Commit** `feat: parse ORCA excited states`.

---

### Task 4: Q-Chem Adapter

**Files:**
- Create: `src/openwfn/parsers/excited/qchem.py`
- Modify: `src/openwfn/ingest.py`
- Modify: `src/openwfn/adapters/iodata.py` only if Task 3 introduced a shared augmentation helper
- Create: `tests/fixtures/qchem/excited/`
- Create: `tests/parsers/test_qchem_excited_states.py`

**Interfaces:**
- Produces: `parse_qchem_excited_states(text: str) -> ExcitedStateCollection | None`.

- [ ] **Step 1: Add project-owned Q-Chem excerpts** covering CIS/TDDFT/TDA, spin-flip/RAS-style output, ADC, EOM families, core/STEX-style output, ΔSCF/MOM summaries, and generic unknown-method states where source grammar permits.
- [ ] **Step 2: Write failing fidelity tests** for exact energies, oscillator strengths, transition moments, roots, multiplicity/symmetry, state character, contributions, diagnostics, and explicit amplitude convention tags.
- [ ] **Step 3: Write failing fallback/malformed tests** for missing strengths, state-only output, malformed transition vectors, repeated roots across jobs, unknown methods, and oversized payloads.
- [ ] **Step 4: Run** `pytest tests/parsers/test_qchem_excited_states.py -q` and verify RED.
- [ ] **Step 5: Implement the adapter and ingestion augmentation** without changing existing IOData interoperability semantics.
- [ ] **Step 6: Run Q-Chem parser, interoperability, and output-property regression suites** and require PASS.
- [ ] **Step 7: Commit** `feat: parse Q-Chem excited states`.

---

### Task 5: Method Classification and Amplitude Semantics

**Files:**
- Create: `src/openwfn/parsers/excited/conventions.py`
- Modify: `src/openwfn/excited_states.py`
- Create: `tests/unit/test_excited_state_conventions.py`

**Interfaces:**
- Produces: `classify_method(source_program: str, source_label: str) -> MethodClassification`.
- Produces: `amplitude_semantics(convention: str) -> AmplitudeSemantics`.
- `MethodClassification`: canonical `family`, preserved `detail`, optional justified transition-kind hint.
- `AmplitudeSemantics`: `defined`, `nto_ready`, `requires_left_state`, `spin_structure`, explanatory note.

- [ ] **Step 1: Write a failing method-matrix test** covering CIS/CIS-like, TDHF/RPA, TDDFT/TDA, spin-flip, ROCIS-like, ADC/CVS, EOM EE/IP/EA/SF, STEOM/similarity-transformed, local/PNO, CASSCF/SA-CASSCF, CASPT2, NEVPT2, RAS, MRCI, NOCI/STEX/core-excitation, ΔSCF/MOM, and unknown/other aliases from applicable programs.
- [ ] **Step 2: Write failing semantic tests** proving exact source labels survive, unknown labels fall back to `other`, percentages stay contributions, and unsupported conventions are not NTO-ready.
- [ ] **Step 3: Define a conservative initial NTO-ready whitelist** only for conventions whose mathematical object is explicitly represented and tested; numeric EOM/ADC/multireference coefficients alone do not qualify.
- [ ] **Step 4: Run** `pytest tests/unit/test_excited_state_conventions.py tests/unit/test_excited_state_model.py -q` and verify RED.
- [ ] **Step 5: Implement deterministic mappings/pattern handlers**; keep program-specific science out of UI/analysis layers.
- [ ] **Step 6: Run all three adapter suites** and require their method/convention expectations to pass.
- [ ] **Step 7: Commit** `feat: classify excited-state method conventions`.

---

### Task 6: Excited-State Analyses and UV–Vis Engine

**Files:**
- Create: `src/openwfn/analysis/excited_states.py`
- Create or extend shared spectral helper: `src/openwfn/spectra.py` from the PR #49 baseline
- Modify: `src/openwfn/constants.py` for `HC_EV_NM = 1239.8419843320026` if no equivalent constant exists
- Modify: `src/openwfn/analysis/registry.py`
- Create: `tests/unit/test_excited_state_analysis.py`
- Create: `tests/unit/test_uvvis.py`

**Interfaces:**
- Registered analyses: `excited-states`, `excited-state`, `uvvis-spectrum`, `transition-dipoles`.
- `excited_state(data, *, state: int, job: int | None = None) -> ResultRecord`.
- `uvvis_spectrum(data, *, job: int | None = None, fwhm_ev: float = 0.20, energy_min_ev: float | None = None, energy_max_ev: float | None = None, points: int | None = None, include_wavelength: bool = True) -> ResultRecord`.
- `MAX_SPECTRUM_POINTS = 100000` unless the rebased shared helper already enforces an equal or stricter bound.

- [ ] **Step 1: Write failing state-analysis tests** for source order, one-based job/state selection, repeated roots across jobs, missing optional fields, and ambiguity when `job` is omitted for a multi-job collection.
- [ ] **Step 2: Write failing Gaussian-broadening tests** for center, half-height at `FWHM/2`, superposition, deterministic grid, `0.20 eV` default, source-stick preservation, and invalid width/range/point count.
- [ ] **Step 3: Write failing wavelength/Jacobian tests** for `lambda_nm = HC_EV_NM / E_eV` and continuous transformation `I_lambda = I_E * HC_EV_NM / lambda_nm**2` in consistent units.
- [ ] **Step 4: Write failing optical-eligibility tests**: `f=0` remains a zero-strength dark stick; missing `f`, negative `f`, and nonpositive energies remain in state data but are excluded from the simulated curve with explicit reasons/warnings.
- [ ] **Step 5: Run** `pytest tests/unit/test_excited_state_analysis.py tests/unit/test_uvvis.py -q` and verify RED.
- [ ] **Step 6: Implement bounded shared broadening and the four analyses** without copying PR #49 math; retain exact sticks and record transformations/provenance.
- [ ] **Step 7: Register analyses** with deterministic defaults and capability gates. Multi-job ambiguity must fail explicitly.
- [ ] **Step 8: Re-run focused analysis/registry tests** and require PASS.
- [ ] **Step 9: Commit** `feat: add excited-state and UV-Vis analyses`.

---

### Task 7: Python API and MCP Parity

**Files:**
- Modify: `src/openwfn/api.py` only for thin convenience wrappers if they materially improve usability
- Modify: `src/openwfn/mcp_server.py` only through generic infrastructure inherited from PR #49
- Create: `tests/integration/test_excited_state_parity.py`
- Modify: `tests/test_mcp_server.py`

**Interfaces:**
- Python: `calc.analyze("excited-states", job=...)`, `calc.analyze("excited-state", state=..., job=...)`, `calc.analyze("uvvis-spectrum", ...)`.
- MCP: existing `run_analysis(path, analysis, format_hint, parameters)`.

- [ ] **Step 1: Write failing Python parity tests** for Gaussian, ORCA, and Q-Chem fixtures comparing direct registry and high-level API scientific fields/provenance.
- [ ] **Step 2: Write failing MCP parity tests** for job/state selection and UV–Vis parameters; verify read-only behavior.
- [ ] **Step 3: Add no excited-state-specific MCP tool**. Add Python convenience wrappers only if tests prove they are thin aliases to registry calls.
- [ ] **Step 4: Run** `pytest tests/integration/test_excited_state_parity.py tests/test_mcp_server.py -q` and require PASS.
- [ ] **Step 5: Commit** `test: enforce excited-state API and MCP parity`.

---

### Task 8: CLI, Exports, and Guided Terminal

**Files:**
- Modify: `src/openwfn/cli.py`
- Modify: `src/openwfn/presentation.py`
- Modify: `src/openwfn/exporters/tables.py`
- Modify: `src/openwfn/exporters/spectra.py`
- Modify: `src/openwfn/interactive.py`
- Modify: `src/openwfn/palette.py`
- Create: `tests/cli/test_excited_states.py`
- Create: `tests/integration/test_uvvis_exports.py`

**Interfaces:**
- `openwfn FILE excited states [--job N]`.
- `openwfn FILE excited state N [--job N]`.
- `openwfn FILE spectra uvvis [--job N] [--fwhm-ev W] [--min-ev X] [--max-ev Y] [--points N] [--domain energy|wavelength]`.
- Exports: row-oriented state CSV/JSON and UV–Vis CSV/JSON/PNG/SVG.
- Guided label: `Analyze excited states and UV-Vis`.

- [ ] **Step 1: Write failing human-output tests** for compact state tables, selected-state details, one-based job ambiguity, dark/non-optical states, warnings/status, and abbreviation of large contributions/amplitudes.
- [ ] **Step 2: Write failing CSV tests** for one row per state and one row per curve point with explicit units/columns.
- [ ] **Step 3: Write failing PNG/SVG tests** for correct energy/wavelength labels, unchanged numeric inputs, and provenance metadata in SVG.
- [ ] **Step 4: Write failing guided-terminal tests** for state table, state detail, and UV–Vis choices.
- [ ] **Step 5: Run focused tests** and verify RED.
- [ ] **Step 6: Implement routing/rendering/export only**; all science must call Task 6 analyses.
- [ ] **Step 7: Run CLI/export/guided suites plus platform smoke** and require PASS.
- [ ] **Step 8: Commit** `feat: expose excited states in terminal workflows`.

---

### Task 9: HTML Report and Offline Workbench

**Files:**
- Modify: `src/openwfn/reporting.py`
- Modify: `src/openwfn/workbench/payload.py`
- Modify: `src/openwfn/workbench/export.py`
- Create: `tests/integration/test_excited_state_report.py`
- Create: `tests/integration/test_excited_state_workbench.py`
- Modify: `scripts/validate_workbench_browser.py` only to add relevant excited-state browser fixtures; preserve existing validation scope

**Interfaces:**
- Report sections: Excited States, selected-state detail, UV–Vis spectrum, optical stick table, method/job/provenance diagnostics.
- Workbench workspace: `Excited States` with one-based job selector when needed, state table/selector, UV–Vis plot, clickable sticks, contributions/diagnostics, and explicit unavailable messages.

- [ ] **Step 1: Write failing report tests** for tables, inline SVG, job/method/provenance, warnings, no network assets, and exact embedded JSON parity with Python ResultRecords.
- [ ] **Step 2: Write failing Workbench payload tests** proving jobs/states/spectra exactly equal registered outputs and missing transition data does not generate invented graphics.
- [ ] **Step 3: Write failing DOM/JavaScript tests** for workspace selection, job/state synchronization, clickable optical sticks, dark/non-optical state display, and shared selected-state state.
- [ ] **Step 4: Run report/Workbench tests** and verify RED.
- [ ] **Step 5: Implement report rendering** from ResultRecords only.
- [ ] **Step 6: Implement the dark Workbench workspace** without changing existing Structure/Orbitals/Density/ESP/Measurements/Vibrations behavior.
- [ ] **Step 7: Run Node/Chromium plus all existing Workbench regressions** and require no JavaScript errors or network requests.
- [ ] **Step 8: Commit** `feat: add excited states to reports and workbench`.

---

### Task 10: Coverage Matrix, Validation, Documentation, and Final Verification

**Files:**
- Create: `docs/science/excited-states-uvvis.md`
- Create: `docs/project/excited-state-method-coverage.md`
- Modify: `docs/reference/cli.md`
- Modify: `docs/reference/python-api.md`
- Modify: `docs/mcp.md`
- Modify: `docs/workbench.md`
- Modify: `docs/limitations.md`
- Modify: `ROADMAP.md`
- Modify: `validation/manifest.json`
- Create: `validation/excited-states/README.md`
- Create validation evidence under: `validation/excited-states/`
- Add/modify tests under: `tests/validation/`

**Interfaces:**
- Coverage matrix columns: program, source/version family, source method label, canonical family, parsed fields, amplitude convention, NTO readiness, fixture/evidence, validation status, limitations.

- [ ] **Step 1: Write a failing coverage-contract test** requiring every canonical family from Task 5 to appear for each applicable source program with at least generic source-state representation; richer optical/amplitude fields must be listed only where fixtures and semantics support them.
- [ ] **Step 2: Add parser-fidelity validation tests** for Gaussian/ORCA/Q-Chem exact source values, absent-vs-zero behavior, multi-job isolation, method labels, and generic fallback.
- [ ] **Step 3: Add analytic/independent UV–Vis validation evidence** for Gaussian FWHM behavior, `HC_EV_NM`, energy↔wavelength conversion/Jacobian, source-stick preservation, and curve exclusion rules. Do not claim cross-program quantum-chemical agreement.
- [ ] **Step 4: Document scientific boundaries**: source oscillator strength versus absorbance/extinction, `0.20 eV` default broadening, wavelength Jacobian, dark/negative/missing optical data, contribution versus amplitude, method conventions, job selection, generic fallback, NTO boundary, and status scope.
- [ ] **Step 5: Run docs/validation tests** and require PASS.
- [ ] **Step 6: Run the complete fresh CI-equivalent verification matrix**: Python 3.10–3.13, lint/repository checks, scientific/reference validation, optional interfaces/MCP, interoperability, wheel build/install smoke, Linux resource benchmark, Windows/macOS smoke, documentation, security, and offline Chromium Workbench validation.
- [ ] **Step 7: Review the whole diff against the approved spec**: no REST, no release bump, no edits to PR #48/#49 branches, no invented scientific values, no duplicated PR #49 infrastructure.
- [ ] **Step 8: Commit final docs/evidence fixes** `docs: document excited-state validation scope`.
- [ ] **Step 9: Open/update one draft excited-state PR** against PR #49 while stacked or `main` after PR #49 merges, state exact method coverage and Experimental boundaries, and require all fresh checks green before marking ready for review.
