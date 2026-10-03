# Excited States and UV–Vis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a method-general, source-faithful excited-state and UV–Vis subsystem for Gaussian, ORCA, and Q-Chem that represents all parser-detectable method families without conflating incompatible amplitude conventions.

**Architecture:** Three focused source adapters normalize program-specific text into one typed `ExcitedStateCollection` containing explicit job blocks, states, transition contributions, and convention-labelled amplitude blocks. Registered analyses consume that model once; CLI, Python, MCP, CSV/JSON/plots, HTML reports, and the offline Workbench render the same `ResultRecord` values rather than implementing separate spectroscopy logic.

**Tech Stack:** Python 3.10+, dataclasses, NumPy, existing `CalculationData.records`, existing analysis registry/`ResultRecord`, matplotlib exporter path, standalone HTML/SVG/JavaScript Workbench, pytest, optional IOData/cclib only where they add source evidence without becoming the public model.

**Spec:** `docs/superpowers/specs/2026-10-03-excited-states-uvvis-design.md`

## Global Constraints

- Keep excited-state scientific status `Experimental` until independent evidence supports narrower promotion.
- Preserve source-reported energies, oscillator strengths, transition dipoles, labels, contributions, amplitudes, and diagnostics; never synthesize missing scientific quantities.
- Preserve amplitude semantics explicitly; TDDFT/RPA X/Y, CIS/CI, ADC, EOM left/right, spin-flip, multireference, and unknown program-specific coefficients are not interchangeable.
- Source state blocks are grouped by source job/block; never combine excited states from one job with geometry, charge, multiplicity, method, or reference metadata from another.
- Every positive excitation energy may expose a derived wavelength; zero/nonpositive energies remain representable but are ineligible for wavelength-domain analysis.
- UV–Vis requires a positive excitation energy and a reported/defined oscillator strength; states without optical strength remain in the state record and are excluded with an explicit reason.
- Broadened spectra retain original source sticks unchanged.
- Continuous energy-to-wavelength transformation applies the absolute Jacobian; do not relabel an evenly spaced energy curve as wavelength.
- Do not label an oscillator-strength-derived simulated spectrum as experimental absorbance or molar extinction.
- Bound state counts, amplitude counts, spectrum points, and parser buffers before allocation.
- REST remains out of scope.
- PR #48 and PR #49 remain untouched by implementation commits.
- **Dependency gate:** do not duplicate generic infrastructure introduced by PR #49. Before Task 1 implementation, either (a) PR #49 is merged into `main` and this branch is rebased onto that `main`, or (b) the user explicitly approves stacking this branch on PR #49 until PR #49 merges.
- Do not publish a release or change stable version metadata in this project.

## Review Focus

1. **Multi-job outputs with several excited-state calculations:** a state request must select the intended job/block and must never inherit metadata from a later/earlier job. Task 1 and each source-adapter task include explicit regression tests.
2. **Dark/zero/negative-energy states:** dark states remain represented; zero or negative excitation energies cannot produce wavelength values or UV–Vis curve points and must be excluded with reasons. Task 6 tests this.
3. **Printed percentages versus amplitudes:** a source line such as “72% HOMO→LUMO” must be stored as a contribution/weight, never as an NTO-ready coefficient. Tasks 1 and 5 test this.
4. **Method aliases and unknown methods:** recognized aliases map to a canonical family while the exact source method label remains preserved; unknown methods still produce generic states without false amplitude semantics. Task 5 tests this.
5. **Huge excited-state/amplitude output:** parsers and analyses reject configured hard ceilings before allocating unbounded arrays. Tasks 1, 2–4, and 6 test this.

---

### Task 1: Universal Excited-State Model, Job Blocks, and Capabilities

**Files:**
- Create: `src/openwfn/excited_states.py`
- Modify: `src/openwfn/capabilities.py`
- Modify: `src/openwfn/data.py` only if a shared structure→minimal-calculation helper is required after rebasing onto the PR #49 baseline
- Test: `tests/unit/test_excited_state_model.py`
- Test: `tests/unit/test_capabilities.py`

**Interfaces:**
- Produces: `TransitionContribution`, `AmplitudeBlock`, `ExcitedState`, `ExcitedStateJob`, `ExcitedStateCollection` frozen dataclasses.
- Produces: `get_excited_state_collection(data: CalculationData | OpenWFNData) -> ExcitedStateCollection`.
- Record key: `CalculationData.records["excited_states"]`.
- Produces inferred capabilities: `excited_states`, `optical_oscillator_strengths`, `transition_dipoles`, `excitation_contributions`, `excitation_amplitudes`, `nto_ready_amplitudes`.

- [ ] **Step 1: Write failing model tests** for finite excitation energies; one-based openWFN state indices; optional source numbering; unavailable-vs-zero optical values; contribution quantity/convention labels; amplitude convention/spin/left-right metadata; immutable tuples; and a collection containing multiple job blocks with repeated source state numbers.

- [ ] **Step 2: Write failing semantic-safety tests** asserting a percent contribution is not accepted as an NTO-ready amplitude, an unknown amplitude convention remains representable but `nto_ready_amplitudes` is false, and per-job source metadata cannot be omitted when more than one excited-state job exists.

- [ ] **Step 3: Write failing resource-limit tests** using constants `MAX_EXCITED_STATES_PER_JOB = 10000` and `MAX_AMPLITUDES_PER_STATE = 1000000`; construction/parsing helpers must reject larger declared payloads before materializing them.

- [ ] **Step 4: Run** `pytest tests/unit/test_excited_state_model.py tests/unit/test_capabilities.py -q` and verify failures are due to missing excited-state types/capabilities.

- [ ] **Step 5: Implement the dataclasses and `get_excited_state_collection`** in `src/openwfn/excited_states.py`. Preserve exact source method label separately from canonical family; wavelength is a derived optional property only for finite positive energy.

- [ ] **Step 6: Add capability inference** based solely on trustworthy typed-record contents. `nto_ready_amplitudes` is true only for convention names explicitly whitelisted in Task 5.

- [ ] **Step 7: Run the focused tests** and require all passing.

- [ ] **Step 8: Commit** with `git commit -m "feat: add typed excited-state records"`.

---

### Task 2: Gaussian Excited-State Adapter

**Files:**
- Create: `src/openwfn/parsers/excited/__init__.py`
- Create: `src/openwfn/parsers/excited/gaussian.py`
- Modify: `src/openwfn/parsers/gaussian/output.py`
- Modify: `src/openwfn/ingest.py`
- Create fixtures: `tests/fixtures/gaussian/excited/`
- Test: `tests/parsers/test_gaussian_excited_states.py`

**Interfaces:**
- Consumes: Task 1 typed model.
- Produces: `parse_gaussian_excited_states(text: str) -> ExcitedStateCollection | None`.
- Gaussian native output ingestion attaches the collection to `CalculationData.records["excited_states"]` for the correct job block without removing vibrational records or other existing records.

- [ ] **Step 1: Add redistribution-safe Gaussian fixtures** covering TDDFT/TDA/CIS-style states, singlet/triplet labels, oscillator strengths, transition dipoles when printed, dominant transitions, spin-flip/core-state examples when available, a dark state, and a multi-Link file with an excited-state job followed by unrelated metadata.

- [ ] **Step 2: Write failing parser-fidelity tests** for exact source energy, oscillator strength, labels, multiplicity/symmetry, contribution coefficients/weights, source order, and exact association with the source Link/job.

- [ ] **Step 3: Write failing malformed/limit tests** for incomplete state lines, nonfinite numeric text, mismatched transition records, repeated source state numbers across different jobs, and declared state/amplitude counts beyond Task 1 limits.

- [ ] **Step 4: Run** `pytest tests/parsers/test_gaussian_excited_states.py -q` and verify expected RED failures.

- [ ] **Step 5: Implement conservative Gaussian job splitting and state parsing**. Keep the exact route/method label in each job; parse richer contributions/amplitudes only when the printed convention is unambiguous.

- [ ] **Step 6: Attach records through native Gaussian ingestion** using the same job geometry/charge/multiplicity/reference metadata boundary already hardened by spectroscopy; add a regression test preventing Link1 cross-job contamination.

- [ ] **Step 7: Run Gaussian parser plus existing Gaussian regression tests** and require all passing.

- [ ] **Step 8: Commit** with `git commit -m "feat: parse Gaussian excited states"`.

---

### Task 3: ORCA Excited-State Adapter

**Files:**
- Create: `src/openwfn/parsers/excited/orca.py`
- Modify: `src/openwfn/ingest.py`
- Modify: `src/openwfn/adapters/iodata.py` only if needed to attach a typed record to an IOData-loaded structure without duplicating parser science
- Create fixtures: `tests/fixtures/orca/excited/`
- Test: `tests/parsers/test_orca_excited_states.py`

**Interfaces:**
- Consumes: Task 1 typed model.
- Produces: `parse_orca_excited_states(text: str) -> ExcitedStateCollection | None`.
- ORCA `.out` continues using the established IOData path for structure/wavefunction data; the native excited-state adapter augments, rather than replaces, that data.

- [ ] **Step 1: Add project-owned ORCA excerpts/fixtures** spanning representative labels for TDDFT/TDA/CIS, ROCIS/spin-flip where available, ADC, EOM/STEOM/local-correlation excited-state output, multireference/CASSCF-family states, and a generic unknown-method state-only block.

- [ ] **Step 2: Write failing fidelity tests** for exact energies, oscillator strengths, transition moments, source root numbering, multiplicity/spin labels, source method text, diagnostics, and contribution/amplitude convention tags.

- [ ] **Step 3: Write failing fallback tests** showing an unknown ORCA excited-state method with parseable state energies is represented as `method_family="other"` while preserving `method_detail`, with no invented oscillator strength/amplitude.

- [ ] **Step 4: Write failing multi-job/limit tests** ensuring repeated root numbers in separate ORCA jobs remain separate and oversized state/amplitude blocks fail before unbounded allocation.

- [ ] **Step 5: Run** `pytest tests/parsers/test_orca_excited_states.py -q` and verify RED failures.

- [ ] **Step 6: Implement the ORCA adapter and ingestion augmentation**. Reuse IOData structure/provenance when trustworthy; create only the minimum structure-bearing `CalculationData` needed to host records when the text output lacks a full wavefunction.

- [ ] **Step 7: Run ORCA parser, interoperability, and output-property regression tests** and require all passing.

- [ ] **Step 8: Commit** with `git commit -m "feat: parse ORCA excited states"`.

---

### Task 4: Q-Chem Excited-State Adapter

**Files:**
- Create: `src/openwfn/parsers/excited/qchem.py`
- Modify: `src/openwfn/ingest.py`
- Modify: `src/openwfn/adapters/iodata.py` only if the Task 3 augmentation helper needs reuse
- Create fixtures: `tests/fixtures/qchem/excited/`
- Test: `tests/parsers/test_qchem_excited_states.py`

**Interfaces:**
- Consumes: Task 1 typed model and Task 3 shared augmentation helper if introduced.
- Produces: `parse_qchem_excited_states(text: str) -> ExcitedStateCollection | None`.

- [ ] **Step 1: Add project-owned Q-Chem excerpts/fixtures** spanning CIS/TDDFT/TDA, spin-flip/RAS-style output where available, ADC, EOM families, core-excitation/STEX-style output, ΔSCF/MOM state summaries, and a generic unknown-method state-only block.

- [ ] **Step 2: Write failing fidelity tests** for exact energies, oscillator strengths, transition dipoles/moments when printed, source root labels, multiplicity/symmetry, state character, contributions, diagnostics, and explicit amplitude convention tags.

- [ ] **Step 3: Write failing fallback/malformed tests** for unknown method labels, missing oscillator strengths, state-only output, malformed transition vectors, repeated roots across jobs, and oversized payloads.

- [ ] **Step 4: Run** `pytest tests/parsers/test_qchem_excited_states.py -q` and verify RED failures.

- [ ] **Step 5: Implement Q-Chem adapter and ingestion augmentation** without changing existing IOData interoperability semantics.

- [ ] **Step 6: Run Q-Chem parser, interoperability, and output-property regression tests** and require all passing.

- [ ] **Step 7: Commit** with `git commit -m "feat: parse Q-Chem excited states"`.

---

### Task 5: Method-Family Classification and Amplitude Convention Registry

**Files:**
- Create: `src/openwfn/parsers/excited/conventions.py`
- Modify: `src/openwfn/excited_states.py`
- Test: `tests/unit/test_excited_state_conventions.py`

**Interfaces:**
- Produces: `classify_method(source_program: str, source_label: str) -> MethodClassification`.
- Produces: `amplitude_semantics(convention: str) -> AmplitudeSemantics`.
- `MethodClassification` contains canonical `family`, preserved `detail`, and transition-kind hints only when justified.
- `AmplitudeSemantics` contains `defined`, `nto_ready`, `requires_left_state`, `spin_structure`, and human-readable convention notes.

- [ ] **Step 1: Write a coverage-matrix test** containing aliases/examples for every family named in the design: CIS/CIS-like, TDHF/RPA, TDDFT/TDA, spin-flip, ROCIS-like, ADC/CVS, EOM EE/IP/EA/SF, STEOM/similarity-transformed, local/PNO, CASSCF/SA-CASSCF, CASPT2, NEVPT2, RAS, MRCI, NOCI/STEX/core-excitation, ΔSCF/MOM, and unknown/other.

- [ ] **Step 2: Write semantic tests** proving source labels are preserved, unknown aliases fall back to `other`, a percent/weight contribution never becomes an amplitude, and unsupported amplitude conventions are never NTO-ready.

- [ ] **Step 3: Define the initial NTO-ready whitelist conservatively** to conventions whose mathematical objects are explicitly represented and tested; do not mark EOM/ADC/multireference conventions ready merely because numeric coefficients exist.

- [ ] **Step 4: Run** `pytest tests/unit/test_excited_state_conventions.py tests/unit/test_excited_state_model.py -q` and verify RED failures.

- [ ] **Step 5: Implement classification/semantics tables** as deterministic data mappings plus narrow program-specific pattern handlers. Avoid program-specific science in UI/analysis modules.

- [ ] **Step 6: Run all three source-adapter suites** and require their method-family/convention expectations to pass.

- [ ] **Step 7: Commit** with `git commit -m "feat: classify excited-state method conventions"`.

---

### Task 6: Excited-State Analyses and UV–Vis Numerical Engine

**Files:**
- Create: `src/openwfn/analysis/excited_states.py`
- Create or refactor shared spectral helper: `src/openwfn/spectra.py` (preferred after PR #49 baseline); if PR #49 already provides an equivalent general helper, extend that file instead
- Modify: `src/openwfn/analysis/registry.py`
- Test: `tests/unit/test_excited_state_analysis.py`
- Test: `tests/unit/test_uvvis.py`

**Interfaces:**
- Produces registered analyses: `excited-states`, `excited-state`, `uvvis-spectrum`, `transition-dipoles`.
- `excited_state(data, *, state: int, job: int | None = None) -> ResultRecord`.
- `uvvis_spectrum(data, *, job: int | None = None, fwhm_ev: float, energy_min_ev: float | None = None, energy_max_ev: float | None = None, points: int | None = None, include_wavelength: bool = True) -> ResultRecord`.
- Pin `HC_EV_NM = 1239.8419843320026` in a shared constants location with a source note in documentation/tests.
- Hard curve ceiling: `MAX_SPECTRUM_POINTS = 100000` unless an existing PR #49 constant already provides the same or stricter bound.

- [ ] **Step 1: Write failing state-analysis tests** for source order, job selection, state selection, dark states, missing optional fields, and repeated source root numbers across jobs.

- [ ] **Step 2: Write failing analytic UV–Vis tests** for Gaussian center/half-height, superposition, deterministic grid, source-stick preservation, exclusion reasons, and nonpositive/nonfinite FWHM/range/point validation.

- [ ] **Step 3: Write failing wavelength/Jacobian tests** asserting `lambda_nm = HC_EV_NM / E_eV`, monotonic reversed wavelength axis as appropriate, and continuous density transformation `I_lambda = I_E * HC_EV_NM / lambda_nm**2` in consistent eV/nm units.

- [ ] **Step 4: Write failing optical-eligibility tests**: zero/negative-energy states remain in `excited-states` but are excluded from UV–Vis; missing oscillator strength is excluded rather than set to zero; a true reported `f=0` line remains a valid dark optical stick with zero strength.

- [ ] **Step 5: Run** `pytest tests/unit/test_excited_state_analysis.py tests/unit/test_uvvis.py -q` and verify RED failures.

- [ ] **Step 6: Implement shared bounded Gaussian broadening and UV–Vis analyses**. Reuse/refactor PR #49 spectral math rather than copy it; preserve exact original sticks and attach transformations/provenance.

- [ ] **Step 7: Register the four analyses** with capability requirements and deterministic defaults. If multiple excited-state jobs exist and `job` is omitted, fail with a clear ambiguity error rather than silently choosing one.

- [ ] **Step 8: Run focused analysis + registry suites** and require all passing.

- [ ] **Step 9: Commit** with `git commit -m "feat: add excited-state and UV-Vis analyses"`.

---

### Task 7: Python API, MCP, and Cross-Program Result Parity

**Files:**
- Modify: `src/openwfn/api.py` only if thin convenience methods materially improve usability
- Modify: `src/openwfn/mcp_server.py` only through the generic parameter path inherited from PR #49; do not add excited-state-specific MCP tools
- Create: `tests/integration/test_excited_state_parity.py`
- Modify: `tests/test_mcp_server.py`

**Interfaces:**
- Python authoritative path: `calc.analyze("excited-states", job=...)`, `calc.analyze("excited-state", state=..., job=...)`, `calc.analyze("uvvis-spectrum", ...)`.
- MCP authoritative path: existing `run_analysis(path, analysis, format_hint, parameters)`.

- [ ] **Step 1: Write failing parity tests** for Gaussian, ORCA, and Q-Chem fixtures proving the generic Python API returns identical scientific `data`, `units`, status, warnings, and analysis provenance to direct registry execution.

- [ ] **Step 2: Write failing MCP parity tests** for job/state selection and UV–Vis parameters; verify scalar parameter validation and read-only behavior.

- [ ] **Step 3: Add no convenience wrappers unless justified**. If wrappers are added, tests must prove they are thin calls returning the same ResultRecord as `analyze`.

- [ ] **Step 4: Run** `pytest tests/integration/test_excited_state_parity.py tests/test_mcp_server.py -q` and require all passing.

- [ ] **Step 5: Commit** with `git commit -m "test: enforce excited-state API and MCP parity"`.

---

### Task 8: CLI, CSV/JSON/PNG/SVG, and Guided Terminal

**Files:**
- Modify: `src/openwfn/cli.py`
- Modify: `src/openwfn/presentation.py`
- Modify: `src/openwfn/exporters/tables.py`
- Modify: `src/openwfn/exporters/spectra.py` from the PR #49 baseline
- Modify: `src/openwfn/interactive.py`
- Modify: `src/openwfn/palette.py`
- Create: `tests/cli/test_excited_states.py`
- Create: `tests/integration/test_uvvis_exports.py`

**Interfaces:**
- CLI: `openwfn FILE excited states [--job N]`.
- CLI: `openwfn FILE excited state N [--job N]`.
- CLI: `openwfn FILE spectra uvvis [--job N] [--fwhm-ev W] [--min-ev X] [--max-ev Y] [--points N] [--domain energy|wavelength]`.
- Export formats: state-table CSV/JSON; UV–Vis CSV/JSON/PNG/SVG.
- Guided workflow label: `Analyze excited states and UV-Vis`.

- [ ] **Step 1: Write failing human-output tests** for compact state tables, selected-state details, job ambiguity, dark/non-optical states, validation/status footers, and abbreviation of large contributions/amplitude blocks.

- [ ] **Step 2: Write failing row-oriented CSV tests** asserting one row per state and one row per spectrum point, with explicit energy/wavelength/intensity columns and no Python-list cells.

- [ ] **Step 3: Write failing plot tests** for valid PNG/SVG, energy-domain axis labels, wavelength-domain axis labels, correct domain transformation, unchanged source arrays, and method/provenance metadata in SVG description.

- [ ] **Step 4: Write failing guided-terminal tests** for the new workflow and choices: state table, state detail, UV–Vis.

- [ ] **Step 5: Run focused CLI/export tests** and verify RED failures.

- [ ] **Step 6: Implement routing/rendering/export only**; all science must call the shared registered analyses from Task 6.

- [ ] **Step 7: Run CLI/export/guided suites** and require all passing on Linux plus the repository platform-smoke matrix.

- [ ] **Step 8: Commit** with `git commit -m "feat: expose excited states in terminal workflows"`.

---

### Task 9: HTML Research Report and Offline Workbench

**Files:**
- Modify: `src/openwfn/reporting.py`
- Modify: `src/openwfn/workbench/payload.py`
- Modify: `src/openwfn/workbench/export.py`
- Create: `tests/integration/test_excited_state_report.py`
- Create: `tests/integration/test_excited_state_workbench.py`
- Modify: `scripts/validate_workbench_browser.py` to add excited-state fixtures only when the test corpus contains the required text outputs; preserve existing real-molecule validation unchanged

**Interfaces:**
- Report renders `excited-states`, selected-state details, and `uvvis-spectrum` from existing ResultRecords only.
- Workbench adds top-level `Excited States` workspace with job selector when needed, state selector/table, UV–Vis plot, optical sticks, selected-state metadata, contributions, diagnostics, and explicit unavailable messages.

- [ ] **Step 1: Write failing report tests** for state table, UV–Vis inline SVG, method/job/provenance text, warnings, no network assets, and exact JSON payload parity with Python ResultRecords.

- [ ] **Step 2: Write failing Workbench payload tests** proving embedded jobs/states/spectrum values exactly equal registered analysis outputs and no transition visualization is fabricated when data are missing.

- [ ] **Step 3: Write failing DOM/JavaScript contract tests** for workspace selection, job/state synchronization, clickable spectral sticks, dark/non-optical state display, and selected-state diagnostics.

- [ ] **Step 4: Run report/Workbench tests** and verify RED failures.

- [ ] **Step 5: Implement specialized HTML rendering** without altering generic sections or recalculating spectroscopy.

- [ ] **Step 6: Implement the dark Workbench workspace** by extending the existing UI identity. Clicking a peak/stick and clicking a state row must update one shared selected-state state object.

- [ ] **Step 7: Run Node/Chromium/browser validation** plus all existing Workbench regression suites and require no new network requests or JavaScript errors.

- [ ] **Step 8: Commit** with `git commit -m "feat: add excited states to reports and workbench"`.

---

### Task 10: Method-Coverage Matrix, Validation Evidence, Documentation, and Final Verification

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
- Create evidence JSON/Markdown under `validation/excited-states/`
- Add/modify validation tests under `tests/validation/`

**Interfaces:**
- Coverage matrix columns: program, source-version family, method label, canonical family, parsed fields, amplitude convention, NTO readiness, fixture/evidence reference, validation status, known limitations.
- Status remains component-specific and defaults to `Experimental`.

- [ ] **Step 1: Create a failing documentation/coverage contract test** requiring every canonical method family from Task 5 to appear in the coverage matrix with at least one of: tested rich adapter, tested generic state representation, or explicit unsupported source grammar with rationale. No family may silently disappear.

- [ ] **Step 2: Add parser-fidelity evidence tests** for Gaussian, ORCA, and Q-Chem fixture values, absent-vs-zero behavior, multi-job safety, and method labels.

- [ ] **Step 3: Add independent/analytic UV–Vis validation evidence** for Gaussian broadening, `HC_EV_NM`, energy↔wavelength conversion/Jacobian, and source-stick preservation. Do not claim cross-program quantum-chemical agreement.

- [ ] **Step 4: Document exact scientific boundaries**: oscillator strength vs absorbance/extinction, energy-domain broadening, wavelength Jacobian, contribution vs amplitude, amplitude conventions, job selection, dark states, generic fallback, NTO boundary, and validation status.

- [ ] **Step 5: Run focused docs/validation tests** and require all passing.

- [ ] **Step 6: Run the complete repository verification matrix** matching current CI: Python 3.10–3.13 test suite, lint/repository checks, scientific/reference validation, optional interfaces/MCP, interoperability, wheel build/install smoke, Linux resource benchmark, Windows/macOS smoke, documentation, security, and offline Chromium Workbench validation.

- [ ] **Step 7: Review the entire diff against the approved spec**. Specifically confirm no REST implementation, no release-version bump, no edits to PR #48/#49 branches, no invented optical/amplitude data, and no duplicated PR #49 infrastructure.

- [ ] **Step 8: Commit final docs/evidence fixes** with `git commit -m "docs: document excited-state validation scope"`.

- [ ] **Step 9: Open or update one draft excited-state PR** against the appropriate base (PR #49 branch while stacked; `main` after PR #49 merges), summarize exact method coverage and Experimental boundaries, and require all fresh checks green before marking it ready for review.
