# Excited States and UV–Vis Design

## Goal

Add a source-faithful, method-general excited-state subsystem for Gaussian, ORCA, and Q-Chem that supports source state inspection and UV–Vis analysis through the same openWFN registry/result architecture used by existing analyses.

The design must be broad enough to represent all parser-detectable excited-state method families without pretending that method-specific amplitudes are mathematically interchangeable. Gaussian, ORCA, and Q-Chem adapters normalize into one typed record. CLI, Python, MCP, reports, exports, and Workbench consume the same registered ResultRecords and never implement separate spectroscopy mathematics.

Initial scientific status is **Experimental** until independent validation evidence justifies narrower promotions.

## Design principles

1. **One universal state model, many source adapters.** Program-specific parsing ends at the typed record boundary.
2. **Source values are preserved.** Energies, oscillator strengths, transition moments, labels, coefficients, and diagnostics remain traceable to the source output.
3. **Method conventions are explicit.** TDDFT/RPA X/Y amplitudes, CIS/CI coefficients, ADC amplitudes, EOM left/right vectors, spin-flip quantities, multireference state data, and ΔSCF states are never silently cast into one another.
4. **Missing data stay missing.** No oscillator strength, transition dipole, amplitude, or multiplicity is invented.
5. **Optical eligibility is capability-based.** A state can be represented even when it cannot contribute to a UV–Vis spectrum.
6. **NTO readiness is separate from excited-state support.** A parsed state is NTO-ready only when a supported, explicitly defined transition-density/amplitude convention is available.
7. **Derived spectra never replace source sticks.** Every UV–Vis result retains the original excitation energies and oscillator strengths.
8. **Bound resource use.** Spectrum grids, state counts, amplitude counts, and parser buffers have explicit limits before allocation.
9. **No REST service in this project.** Python, CLI, local MCP, HTML report, and offline Workbench remain the supported surfaces.

## Scope

### Source programs

The first subsystem targets:

- Gaussian text outputs
- ORCA text outputs
- Q-Chem text outputs

Each source adapter may use a native parser, cclib-backed evidence, or both, but the normalized record and public analyses are independent of the parser implementation.

### Method families

The model is intentionally method-general and may represent, when the source output supplies sufficient information:

- CIS and CIS-like variants
- TDHF / RPA
- TDDFT and TDA
- spin-flip and spin-adapted response variants
- ROCIS-like methods
- ADC families and core-valence-separated variants
- EOM-CC excitation, ionization, electron-attachment, and spin-flip families
- STEOM / similarity-transformed excited-state variants
- PNO/DLPNO or related local-correlation excited-state variants when source states are reported
- CASSCF / state-averaged CASSCF
- CASPT2 and related perturbative multireference corrections
- NEVPT2 and related multireference corrections
- RAS-CI / RAS-SF and related restricted-active-space methods
- MRCI and other source-reported multireference excited states
- NOCI / STEX and source-reported core-excitation approaches
- ΔSCF / MOM excited states
- generic source-reported states from methods not yet assigned a richer adapter

This list defines representational scope, not a claim that every program/version prints every field for every method.

## Typed data model

### `ExcitedStateRecord`

Stored additively in `CalculationData.records["excited_states"]` without changing `MODEL_SCHEMA_VERSION` unless a later implementation proves that unavoidable.

Fields:

- `source_program`
- `source_program_version`
- `method_family`
- `method_detail`
- `reference_state`
- `states: tuple[ExcitedState, ...]`
- `parser_provenance`
- optional source/job metadata relevant to state interpretation

### `ExcitedState`

Required:

- one-based openWFN `index`
- source state identifier/number when available
- excitation energy in eV
- derived wavelength in nm when energy is positive

Optional source-reported fields:

- oscillator strength
- transition dipole vector and its source unit/convention
- multiplicity
- symmetry / irreducible representation
- state label
- spin expectation or spin diagnostic
- state character / root label
- transition kind (`valence`, `core`, `ionization`, `electron_attachment`, `spin_flip`, `other`)
- source-reported dominant configurations or transitions
- method diagnostics
- one or more amplitude blocks

Every optional value distinguishes unavailable from zero.

### `TransitionContribution`

For source-reported dominant orbital/configuration contributions when the source semantics are clear:

- occupied/source orbital identifier
- virtual/target orbital identifier
- spin/channel labels when available
- coefficient or source-reported weight
- quantity name (`coefficient`, `percent`, `weight`, etc.)
- exact convention label

A printed percentage is not automatically an amplitude.

### `AmplitudeBlock`

A generic container for mathematically defined amplitude data:

- `convention`
- `spin_block`
- `left_or_right`
- dimensional metadata
- orbital/configuration indices
- numeric values
- normalization diagnostics if meaningful

Examples of convention labels include `cis-coefficient`, `tda-x`, `tddft-x`, `tddft-y`, `eom-right`, `eom-left`, `adc-amplitude`, or a program-specific explicit convention.

Unknown conventions are preserved as source data but are not eligible for NTO or other transformations that require a defined mathematical meaning.

## Capability model

Inferred capabilities include:

- `excited_states`
- `optical_oscillator_strengths`
- `transition_dipoles`
- `excitation_contributions`
- `excitation_amplitudes`
- `nto_ready_amplitudes`

A calculation may have `excited_states` while lacking all other capabilities.

## Source adapter architecture

Each program gets a focused adapter that emits the same typed record.

### Gaussian adapter

Must associate each state block with the correct job/link section and molecular/reference metadata. Multi-Link outputs must not mix excited-state data from one job with charge, multiplicity, geometry, method, or energy from a later job.

### ORCA adapter

Must preserve ORCA method labels, root/state numbering, multiplicity/spin information, oscillator strengths/transition moments when present, and method-specific diagnostics without mapping them onto Gaussian terminology.

### Q-Chem adapter

Must preserve Q-Chem method/state labels, oscillator strengths/transition moments when present, state character and method-specific diagnostics, and explicit amplitude conventions when available.

### Generic fallback

If a supported source program/method yields only state energies and labels, openWFN still records those states. It does not fabricate optical or amplitude properties.

## Registered analyses

### `excited-states`

Returns all source states in source order with compact state metadata, optical availability, method information, and diagnostics.

### `excited-state`

Parameter: `state` (one-based).

Returns the full record for one state, including contributions and amplitude metadata when available.

### `uvvis-spectrum`

Requires positive excitation energies and oscillator strengths for at least one state.

Returns:

- source stick lines
- energy-domain spectrum arrays
- optional wavelength-domain arrays
- broadening metadata
- excluded/non-optical states with reasons
- warnings
- provenance

### `transition-dipoles`

Optional convenience analysis if transition dipoles are present. This remains a projection of the same typed record, not a separate parser.

## UV–Vis mathematics

### Source sticks

The canonical optical stick data are excitation energy `E_i` and source oscillator strength `f_i`.

No state lacking a reported or independently defined oscillator strength is assigned one.

### Default broadening

Default spectral broadening is performed in **energy space**, because a Gaussian with fixed width in eV has a clear interpretation independent of wavelength reparameterization.

Initial default:

- Gaussian line shape
- deterministic bounded energy range
- explicit width parameter in eV
- source sticks retained unchanged

The exact default width is documented and tested; users can override it.

### Wavelength representation and Jacobian

For positive excitation energy:

`lambda_nm = hc / E`

with a pinned physical constant and provenance.

When a continuous energy-domain density is transformed to wavelength-domain density, openWFN applies the required absolute Jacobian:

`I_lambda(lambda) = I_E(E(lambda)) * |dE/dlambda|`

where `|dE/dlambda| = hc / lambda^2` in consistent units.

This prevents the common but scientifically incorrect practice of merely relabeling an evenly spaced energy curve as wavelength.

Source stick oscillator strengths themselves remain source values; the Jacobian applies to the continuous density representation, not to redefining the original `f_i`.

### Absolute absorbance / extinction

openWFN does not label a broadened oscillator-strength curve as experimental absorbance or molar extinction unless the required physical convention and constants are explicitly implemented and documented. The first implementation is an oscillator-strength-derived simulated spectrum.

## CLI

Human-facing commands:

```bash
openwfn calculation.out excited states
openwfn calculation.out excited state 3
openwfn calculation.out spectra uvvis
```

Spectrum controls should include explicit energy/wavelength range, width, number of points, and domain where appropriate.

Exports:

- CSV: one row per state or spectrum point
- JSON: complete ResultRecord
- PNG/SVG: publication-oriented plot generated from the same ResultRecord arrays

Human output stays compact and deterministic. Large amplitude arrays are abbreviated unless structured output is requested.

## Python API

The generic registry path remains authoritative:

```python
calc.analyze("excited-states")
calc.analyze("excited-state", state=3)
calc.analyze("uvvis-spectrum", ...)
```

Convenience wrappers are optional and must be thin registry calls only.

## MCP

The local read-only MCP interface exposes the same registered analyses through `list_analyses` and `run_analysis`.

If the spectroscopy PR's scalar parameter-forwarding support has landed in `main`, reuse it. If not, the excited-state implementation must not duplicate or fork that logic; coordinate the dependency cleanly before implementation.

MCP creates no files and performs no alternate excited-state calculations.

## HTML research report

Add specialized sections that render existing ResultRecords:

- Excited States table
- selected-state details
- UV–Vis plot
- optical stick table
- method/provenance diagnostics

The embedded machine-readable JSON remains authoritative. HTML rendering never recalculates excitation energies, oscillator strengths, or spectra.

## Offline Workbench

Add an `Excited States` workspace while preserving all existing workspaces.

The workspace contains:

- state table/list
- selected-state metadata and diagnostics
- UV–Vis spectrum
- clickable optical sticks/peaks synchronized with selected state
- transition/contribution display when available
- explicit unavailable messages when transition data are missing

No orbital animation, charge-transfer arrow, electron-hole plot, or NTO is invented from insufficient data. Those visualizations require their own mathematically supported records.

## NTO boundary

NTO is a separate subsequent project.

This project prepares NTO by preserving method-defined amplitudes and exposing `nto_ready_amplitudes` only when the convention is explicitly supported.

Before any NTO calculation, the later NTO project must define, per supported method:

- excitation convention
- required X/Y or CI/EOM/ADC objects
- AO/MO metric treatment
- spin blocks
- normalization
- whether left/right states are required

Unsupported amplitude conventions fail explicitly rather than being coerced.

## Validation strategy

Validation is layered.

### 1. Parser fidelity

For redistribution-safe fixtures from Gaussian, ORCA, and Q-Chem:

- exact excitation energies
- oscillator strengths
- transition dipoles when present
- multiplicity/symmetry/state labels
- contributions/amplitudes where semantically defined
- source order
- absent-vs-zero behavior
- malformed/incomplete output handling
- multi-job association safety

### 2. Cross-program invariants

For intentionally comparable small calculations where legal fixtures are available:

- unit conversions
- wavelength conversion
- state ordering policy
- optical eligibility
- deterministic ResultRecord schema

This does not claim the different programs should give identical quantum-chemical results.

### 3. Derived spectrum validation

Analytic tests cover:

- Gaussian broadening center and width
- linear superposition
- deterministic grids
- bounded point counts
- energy-to-wavelength conversion
- wavelength Jacobian
- preservation of source sticks

### 4. Independent scientific evidence

Promotion beyond Experimental requires independent source/reference evidence appropriate to each parser/method family. Validation status may differ by component; parser fidelity for one method family does not validate another family's amplitudes.

## Status model

Initially:

- excited-state framework: Experimental
- Gaussian adapter: Experimental
- ORCA adapter: Experimental
- Q-Chem adapter: Experimental
- UV–Vis broadening/conversion: Experimental until independent validation is recorded
- method-specific amplitudes: Experimental per supported convention
- generic unknown-method state summaries: Experimental

Later promotions can be narrower, for example source energy/oscillator-strength fidelity may become Validated while an amplitude convention remains Experimental.

## Error and safety behavior

Explicit failures for:

- no excited-state records
- requested state index outside range
- nonpositive/nonfinite excitation energy where wavelength is required
- no optical states for UV–Vis
- malformed oscillator strengths or transition vectors
- ambiguous amplitude convention
- excessive state/amplitude/curve sizes
- cross-job metadata ambiguity

Partial results are allowed when trustworthy state data exist but optional fields are missing. Warnings must name what is absent or excluded.

## Efficiency strategy

The efficient implementation sequence is:

1. universal typed model and capability inference
2. source adapters normalized into that model
3. one shared excited-state/UV–Vis numerical service
4. registry/API/MCP parity
5. one shared CLI/export layer
6. report rendering from ResultRecords
7. Workbench rendering from ResultRecords
8. validation evidence and documentation

Program and method coverage grows by adding parser adapters and fixtures, not by duplicating the analysis/UI stack.

## Branch and dependency policy

- This design lives on `feat/excited-states-uvvis`, separate from PR #48 and PR #49.
- PR #48 Hirshfeld remains untouched.
- PR #49 vibrational spectroscopy remains untouched.
- Implementation should be based on the current `main` after required shared infrastructure from PR #49 is merged, or explicitly rebase/cherry-pick only the minimal shared infrastructure if the user chooses not to merge PR #49 first.
- Do not publish a release or change stable version metadata as part of implementation.

## Success criteria

The project is successful when:

1. Gaussian, ORCA, and Q-Chem outputs normalize excited states into the same typed model.
2. All parser-detectable method families can be represented without false equivalence between amplitude conventions.
3. Optical states produce the same UV–Vis ResultRecord through Python, CLI, and MCP.
4. CSV/JSON/PNG/SVG, HTML report, and Workbench render the same registered numerical data.
5. Missing optical/amplitude information fails or degrades explicitly, never by invention.
6. Multi-job outputs cannot silently mix state data with unrelated metadata.
7. Validation status remains conservative and component-specific.
8. The design leaves a mathematically clean path for a later NTO project.
