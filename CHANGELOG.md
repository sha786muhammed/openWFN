# Changelog

All notable changes to openWFN are documented in this file.

## [0.8.2] - 2026-09-28

### Fixed

- Real Gaussian post-HF method labels such as `UMP2-FC`, `UMP3-FC`, and `UCISD-FC` now preserve the explicit warning when openWFN analyzes the available SCF density rather than a correlated post-SCF density.
- Restricted closed-shell calculations that omit an explicit spin-density matrix can now derive the scientifically defined channels `alpha = beta = total/2` and `spin = 0`, including density integration and cube export.
- Valid one-electron and empty-spin-channel frontier cases now return explicit partial results with unavailable quantities represented as null instead of failing the entire frontier analysis.

### Validation

- The patch was developed with regression tests first and then verified on Python 3.10–3.13, macOS, Windows, wheel/package smoke tests, documentation, security checks, and the repository scientific validation suite.
- A separate post-fix audit passed the independent external benchmark corpus plus an 88-workflow CLI/API matrix and focused UHF, RHF, post-HF, ghost, and ECP edge cases.
- This is a corrective patch release; it does not broaden the documented validation scope beyond the named fixtures, tolerances, and capability boundaries.

## [0.8.1] - 2026-09-28

### Added

- Added permanent regression fixtures for ECP effective charges, ghost centers, post-HF calculations using an SCF density, unrestricted cases with a higher beta HOMO, ROHF classification, zero-spin density integration, and density-grid chunk equivalence.
- Added the spin-complete `frontier-all` registered analysis and `spin="all"` Python/CLI workflow for unrestricted calculations.
- Added Löwdin overlap conditioning diagnostics and explicit density/electron-count provenance fields in structured results.

### Changed

- Population charges, nuclear ESP, cube atom charges, and related special-case logic now use source effective nuclear charges when FCHK provides them.
- Expected density electron counts now prefer source FCHK electron records; deterministic fallbacks emit warnings.
- Density grids are evaluated in chunked AO batches to reduce peak memory without changing Cartesian grid order or numerical values.
- Batch workflows preserve usable `partial` results and include frontier spin selection in reproducibility fingerprints.
- Scientific warnings from analyses and parser provenance are merged rather than one source replacing the other.

### Fixed

- Conservation errors can no longer remain silent clean successes: inconsistent population or density results retain their numbers but return `status="partial"`, Experimental validation status, and an explanatory warning.
- Zero-target spin-density validation now uses an absolute-error criterion rather than an invalid relative-error calculation.
- Density cube results are labeled Validated only after the exact generated grid passes electron-conservation validation.
- Ghost centers no longer contribute as physical nuclei to formula, center of mass, inferred bonds, fragments, or nuclear ESP.
- Unrestricted frontier analysis no longer hides the beta channel when the spin-complete view is requested; the overall HOMO is selected from both channels.
- HOMO/LUMO selection is occupation aware instead of blindly assuming the LUMO is adjacent to the HOMO index.
- Restricted open-shell and unrestricted references are distinguished from restricted closed-shell calculations.
- Post-HF analyses explicitly identify when the available SCF density is being used rather than implying a post-SCF density.

### Scientific boundaries

- ECP, ghost, UHF, ROHF, and post-HF fixtures in this release are implementation/regression evidence; they do not by themselves establish broad independent validation across all methods and chemical systems.
- The default density grid spacing of 0.15 bohr remains an accuracy/performance starting point. Quantitative research should converge spacing and padding and inspect result status/warnings.
- openWFN still does not claim general post-SCF density support unless a supported correlated density is explicitly parsed and selected.

## [0.8.0] - 2026-09-28

### Added

- Added strict finite-value validation across public scientific models and result envelopes, including nested NumPy arrays.
- Added explicit regression coverage for invalid spin channels, density kinds, population methods, ESP kinds, atom indices, and non-finite scientific data.

### Changed

- High-level Python analysis helpers now return the same provenance-bearing `ResultRecord` type as named analyses.
- Public geometry documentation now states the one-based atom numbering used by the CLI and high-level Python API, while internal arrays remain zero-based.
- The Python guide now identifies `analyze(name)` as the preferred automation interface and the specialized methods as discoverable convenience helpers.

### Fixed

- Invalid analysis options now fail immediately instead of falling through to a default spin channel or being masked by missing calculation data.
- High-level analysis results now preserve source provenance consistently.

### Scientific boundaries

- Existing capability labels remain authoritative: methods marked **Validated** retain their documented evidence scope, while **Experimental** and **Unsupported** capabilities keep those labels.
- Gaussian formatted-checkpoint files remain the primary source for full wavefunction analysis in this release.

## [0.8.0a2] - 2026-09-28

### Added

- Added an installed-example command and packaged water fixture so the first analysis works from a wheel without cloning the repository.
- Added a deterministic batch-throughput benchmark with machine-readable timing, count, version, and parent-process memory evidence.
- Added contributor, maintainer, security, conduct, citation, provenance, and third-party-attribution records.

### Changed

- Parallel batches now use a bounded completion-driven queue, persist each finished input immediately, and retain deterministic manifest ordering.
- Stable and pre-release installation instructions are separated throughout the README and handbook.
- Wheel and platform CI now exercise packaged examples and real multi-worker batch execution.

### Fixed

- Deferred Matplotlib imports until a plotting command runs, avoiding plotting startup work for ordinary CLI commands.
