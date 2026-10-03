# Vibrational Spectroscopy Design

## Purpose

Add source-faithful vibrational spectroscopy to openWFN without changing the scientific meaning of existing analyses or touching PR #48. The new subsystem covers parsed vibrational modes, IR stick/broadened spectra, Raman activities/stick/broadened spectra, normal-mode displacement data, and consistent exposure through the current CLI, Python API, MCP, HTML research report, guided terminal, and offline Workbench.

REST is explicitly out of scope for this project because openWFN does not currently expose a remote REST service.

## Product boundary

This feature is a post-processing and source-property workflow. openWFN will preserve source-reported vibrational quantities and only derive spectrum curves through an explicitly documented broadening operation. It will not silently infer unavailable quantities, relabel Raman activity as Raman intensity, invent temperature or laser parameters, or claim that a successful parser establishes universal scientific validation.

Initial status is `Experimental`. Promotion requires independent reference evidence and a documented supported-source boundary.

## Data model

Keep `MODEL_SCHEMA_VERSION = "2.0"` unchanged for this project. Store vibrational information as additive typed records attached through `CalculationData.records` so existing calculation consumers remain compatible.

Introduce focused immutable domain objects:

- `VibrationalMode`
  - one-based public mode index
  - signed frequency in cm^-1
  - `imaginary: bool`
  - optional reduced mass in amu
  - optional force constant in mDyne/Å
  - optional IR intensity in km/mol
  - optional Raman activity in Å^4/amu
  - optional source symmetry label
  - Cartesian displacement vector per atom, when supplied by the source
- `VibrationalRecord`
  - tuple of `VibrationalMode`
  - source program and source-program version when known
  - harmonic/anharmonic/source-method metadata when known
  - parser provenance
  - explicit availability flags for IR, Raman, and displacements

Imaginary modes must remain numerically distinguishable from real modes. Public output should display them clearly instead of silently taking absolute values.

## Source ingestion

### Initial source scope

Start with Gaussian frequency outputs because they are the most directly aligned with the requested workflow and can provide frequencies, reduced masses, force constants, IR intensities, Raman activities, and normal-mode vectors in one source family.

Parser behavior must be source-faithful:

- preserve source ordering of modes;
- preserve source numerical values to parser precision;
- preserve missing values as unavailable rather than zero;
- distinguish absent Raman activities from zero Raman activity;
- distinguish missing normal-mode vectors from an empty displacement;
- record parser/source provenance in the result envelope.

Additional source programs such as ORCA and Q-Chem belong in later source-adapter extensions after the Gaussian contract and validation corpus are stable.

## Scientific analyses

Expose four independent registered analyses so callers can request only the data needed:

1. `vibrations`
   - source mode table and diagnostics;
   - no broadening;
   - reports number of modes, number of imaginary modes, and source availability.

2. `ir-spectrum`
   - source IR stick lines plus optional broadened curve;
   - default Gaussian broadening;
   - default FWHM: 20 cm^-1;
   - deterministic frequency grid;
   - must retain original stick frequencies/intensities in every result.

3. `raman-spectrum`
   - source Raman activities plus optional broadened activity curve;
   - default Gaussian broadening;
   - default FWHM: 20 cm^-1;
   - call the vertical quantity Raman activity unless a separately defined intensity model is implemented later;
   - do not introduce temperature-, excitation-wavelength-, polarization-, or instrument-dependent intensity corrections in this project.

4. `normal-mode`
   - one requested one-based mode index;
   - returns source displacement vectors and the mode metadata;
   - fails explicitly when displacement vectors are unavailable.

### Spectrum convention

For Gaussian broadening, FWHM and standard deviation satisfy

`sigma = FWHM / (2 * sqrt(2 * ln(2)))`.

The broadened curve is a visualization/post-processing representation. The source stick values remain authoritative source properties and must be returned alongside the curve.

The default frequency range should be derived deterministically from available source modes with a bounded margin, while explicit `frequency_min_cm1`, `frequency_max_cm1`, and `points` parameters override defaults. Inputs that would produce an unreasonably large grid must be rejected before allocation using the same bounded-resource philosophy as the existing density/orbital workflows.

## Result contract

All interfaces consume the same `ResultRecord` contract.

### `vibrations`

`data` contains:

- `mode_count`
- `imaginary_mode_count`
- `ir_available`
- `raman_available`
- `displacements_available`
- `modes`: list of structured mode objects

Units are declared through `ResultRecord.units`; do not embed ambiguous unit strings into numeric values.

### `ir-spectrum` / `raman-spectrum`

`data` contains:

- `spectrum_type`
- `lines`: original source stick data
- `frequency_cm1`: broadened-grid x values
- `intensity`: broadened y values
- `broadening`: `{type, fwhm_cm1}`
- requested/actual frequency range

The Raman analysis names the y quantity `activity` in metadata and documentation even if a generic plotting array key is used internally.

### `normal-mode`

`data` contains:

- selected mode metadata
- atomic displacement vectors in source-normalized Cartesian convention
- atom ordering sufficient to map vectors back to the molecular geometry

## CLI

Preserve the existing deterministic presentation style rather than introducing a new terminal framework.

Add commands conceptually equivalent to:

```bash
openwfn calculation.log vibrations
openwfn calculation.log spectra ir
openwfn calculation.log spectra raman
openwfn calculation.log vibrations mode 3
```

The normal human renderer shows:

- compact vibrational mode table;
- source availability;
- validation/result status;
- no huge numeric curve arrays by default.

Long spectrum arrays follow the existing rule: abbreviated in human output, complete under `--verbose` or `--format json`.

Support machine-readable JSON through the existing renderer. CSV export for mode tables and spectra must use row-oriented scientific tables rather than serializing Python list syntax into one CSV cell.

Add optional publication-quality plot export for IR/Raman. Plot generation must be deterministic and separate from the numerical result calculation.

## Python API

Preserve the generic registry API:

```python
calc.analyze("vibrations")
calc.analyze("ir-spectrum", fwhm_cm1=20.0)
calc.analyze("raman-spectrum", fwhm_cm1=20.0)
calc.analyze("normal-mode", mode=3)
```

Convenience methods may be added only as thin wrappers over `run_analysis_safe`; they must not contain independent scientific implementations.

The returned object remains `ResultRecord` so Python, CLI, batch, report, and MCP can be parity-tested.

## MCP

Extend the existing read-only registered-analysis path rather than creating spectroscopy-specific MCP code. Once the analyses are in the registry, `list_analyses()` and `run_analysis()` expose them automatically subject to capability checks.

MCP returns the complete structured `ResultRecord.as_dict()` including:

- source lines;
- broadened arrays when requested/defaulted;
- units;
- status;
- validation status;
- warnings;
- provenance.

The MCP adapter does not create plots, HTML, or files. It remains read-only.

## HTML research report

Preserve the existing light scientific-report identity, but add spectroscopy-specific rendering rather than dumping large arrays into generic key/value rows.

For `vibrations`, render a compact table with one row per mode and columns for frequency, imaginary flag, IR intensity, Raman activity, reduced mass, force constant, and optional symmetry label.

For `ir-spectrum` and `raman-spectrum`, render a self-contained inline SVG spectrum plus a compact peak/stick table. The report remains network-independent and embeds the numerical `ResultRecord` JSON for reproducibility.

Do not turn the research report into the Workbench. It remains a portable scientific record optimized for reading, printing, archiving, and sharing.

## Offline Workbench

Preserve the existing dark Workbench visual identity and offline/no-upload behavior.

Add a `Vibrations` workspace. Within that workspace:

- mode selector/table;
- selected mode properties;
- 3D normal-mode displacement visualization using the existing molecular viewer;
- displacement arrows/vectors when source vectors are available;
- amplitude control affects visualization only and never modifies scientific values;
- clear unavailable state when vectors are absent.

Add IR and Raman spectrum panels to the Vibrations workspace rather than adding many top-level sidebars. Spectrum lines/curves are rendered from embedded result data.

Selecting a mode from the table or spectrum should update the mode detail view and 3D displacement visualization when vectors are available.

The Workbench remains a visualization/teaching surface, not the numerical record of authority. JSON/CSV/report results remain the scientific record.

## Guided terminal

Add spectroscopy under the existing workflow palette without replacing the current interaction model. A new workflow label such as `Analyze vibrations and spectra` should route users to:

- mode table;
- IR spectrum analysis;
- Raman spectrum analysis;
- normal-mode inspection.

Results still render through the shared presentation layer.

## Capability gating and failures

The registry must distinguish at least:

- no vibrational record -> analysis unavailable;
- frequencies present but no IR intensities -> `vibrations` succeeds, `ir-spectrum` fails as unsupported for that input;
- frequencies present but no Raman activities -> `vibrations` succeeds, `raman-spectrum` fails as unsupported for that input;
- mode metadata present but no displacement vectors -> `normal-mode` fails explicitly;
- invalid mode index -> clear validation error;
- malformed or inconsistent vector count -> parser/result failure, never silent truncation;
- non-finite source values -> reject before creating `ResultRecord`;
- excessive requested spectrum grid -> reject before allocation.

Partial status is appropriate when usable source data exist but a documented validation/conservation/consistency gate fails. Missing required data should return failed/unsupported rather than partial.

## Validation strategy

Validation has three layers and the documentation must keep them distinct.

### Parser fidelity

Commit redistribution-safe Gaussian examples spanning:

- water or another nonlinear triatomic;
- linear molecule to exercise `3N-5` mode count;
- molecule with an imaginary mode;
- molecule with IR and Raman data;
- file where Raman data are absent;
- file where normal-mode vectors are present.

Compare parsed values directly with committed source excerpts/expected values.

### Numerical spectrum validation

For broadening, validate against closed-form Gaussian expectations:

- peak center equals source line frequency;
- single-line peak reaches the expected normalized/source-scaled value under the documented convention;
- symmetry around the center;
- FWHM property at half maximum;
- multi-line spectrum equals the sum of independently calculated single-line contributions.

### Independent source/reference checks

Add at least one independent comparison route before promotion beyond Experimental. The initial implementation may land Experimental with parser-fidelity and analytic broadening tests while clearly recording the remaining external-reference boundary.

## Interface parity

For the same input and parameters, CLI JSON, Python API, batch/report embedded JSON, and MCP must return numerically identical `ResultRecord` scientific fields. Human HTML/Workbench rendering may differ visually but must be derived from those same values.

## Documentation

Add dedicated scientific documentation covering:

- what a harmonic vibrational mode is;
- frequency sign/imaginary-mode convention;
- source vs derived values;
- IR intensity units;
- Raman activity vs Raman intensity distinction;
- broadening definition and default FWHM;
- limitations and validation scope;
- CLI/Python/MCP examples;
- report and Workbench behavior.

Update the roadmap and validation manifest only with statuses supported by evidence. Do not mark this feature `Validated` merely because tests pass.

## Release and PR boundary

This work lives on `feat/0.12-vibrational-spectroscopy`, branched from `main`. PR #48 (`feat/0.11-hirshfeld-clean`) remains untouched.

Do not publish to PyPI or merge automatically as part of implementation. The feature PR should remain independently reviewable, with its own validation evidence and release notes.

## Success criteria

The feature is ready for review when:

1. Gaussian vibrational records are parsed into typed additive records without changing model schema 2.0.
2. `vibrations`, `ir-spectrum`, `raman-spectrum`, and `normal-mode` use one shared scientific implementation path.
3. CLI, Python, batch/report, and MCP numerical parity tests pass.
4. HTML report renders mode tables and offline SVG spectra from the same `ResultRecord` data.
5. Workbench renders the Vibrations workspace and normal-mode vectors without changing scientific values.
6. Missing IR/Raman/vector data fail explicitly and scientifically correctly.
7. Broadening passes analytic tests and resource bounds.
8. Documentation accurately distinguishes source data, derived curves, Experimental status, and Raman activity from intensity.
9. Existing tests and current stable interfaces remain green.
10. PR #48 is unchanged.
