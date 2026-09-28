# Changelog

All notable changes to openWFN are documented in this file.

## [0.8.1] - Unreleased

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
- Added a read-only repository preflight and built-archive content tests for release consistency.

### Changed

- Parallel batches now use a bounded completion-driven queue, persist each finished input immediately, and retain deterministic manifest ordering.
- Stable and pre-release installation instructions are separated throughout the README and handbook.
- Wheel and platform CI now exercise packaged examples and real multi-worker batch execution.
- Release smoke testing now verifies summary, frontier-orbital, report, and offline workbench workflows from the built wheel.

### Fixed

- Deferred Matplotlib imports until a plotting command runs, avoiding plotting startup work for ordinary CLI commands.

### Alpha limitations

- Scientific support and validation boundaries are unchanged from 0.8.0a1.
- Gaussian formatted-checkpoint files remain the primary source for full wavefunction analysis.
- Experimental and Unsupported capabilities retain their existing labels.

## [0.8.0a1] - 2026-09-21

### Added

- Added a versioned calculation boundary with schema `2.0`, immutable source identity, parser provenance, named transformations, and canonical source-format tracking.
- Added a versioned analysis registry and result envelope carrying analysis identity, units, validation status, warnings, timing, provenance, and structured failures.
- Added multi-analysis batch manifests, recursive directory discovery, deterministic CSV indexing, and crash-safe resume from persisted result envelopes.

### Changed

- Unified named analysis execution across the Python API and high-throughput batch workflows.
- Redesigned the documentation website around task-oriented learning, CLI/API reference material, scientific-method documentation, and a single project identity.
- Added dedicated documentation integration testing without expanding the standard Python-version test matrix.

### Fixed

- Accepted adjacent signed real fields, omitted redundant atom counts, blank character arrays, and producer-specific title text in Gaussian formatted-checkpoint files.
- Accepted case-insensitive V2000 markers, common XYZ trailing columns/blank lines, and standard PDB atom-name element inference.
- Made `doctor` type-aware for molecular calculations, Gaussian metadata, and cube grids, with clean capability errors for incompatible analysis commands.
- Restored the documented file-only CLI behavior before argument parsing.
- Replaced exhaustive all-pairs bond detection with an equivalent spatial search for finite molecular coordinates.

### Alpha limitations

- Gaussian formatted checkpoint files remain the primary wavefunction input for quantitative orbital, density, population, and electrostatic analyses.
- The `2.0` model and result schemas are alpha interfaces and may receive compatibility-driven refinements before `0.8.0`.
- Experimental and Unsupported scientific capabilities remain labeled as such in machine-readable results and documentation.

## [0.7.2] - 2026-09-12

### Added

- Added Gaussian real spherical basis support for 5D, 7F, 9G, and 11H shells through angular momentum `l=5`.
- Added configurable `--spacing` and `--padding` controls to `openwfn ... validate` for practical validation-grid sizing.

### Changed

- Routed molecular summaries through the shared result renderer so table, plain, JSON, CSV, and output-file workflows stay consistent.
- Structure exporters now report the installed package version dynamically in MOL and SDF headers.
- Updated release documentation and capability boundaries to reflect spherical D/F/G/H support.

### Fixed

- Preserved backward-compatible `Atoms:` summary output while adding structured summary data.
- Restored clean actionable `.chk` conversion errors through the shared CLI error boundary.
- Kept the established ``requires `formchk` `` error contract for missing Gaussian utilities.

## [0.7.1] - 2026-09-11

### Fixed

- Corrected command-first batch routing and help routing after an input file.
- Repaired geometry and connectivity routing in the v0.7 CLI.
- Fixed invalid JavaScript in the standalone offline workbench.
- Improved overwrite guidance for existing output files.
- Rebalanced the documentation header and homepage hero for compact desktop and mobile layouts.

## [0.7.0] - 2026-09-11

### Added

- Unified typed calculation model and strict Gaussian FCHK, CHK, cube, log, and output parsers.
- XYZ, PDB, MOL, and SDF structure interoperability.
- Direct and guided CLI workflows with structured table, plain, JSON, and CSV results.
- Normalized Cartesian Gaussian basis evaluation, orbitals, total/spin density, and cube export.
- Mulliken and symmetric Löwdin populations with analytic AO overlap matrices.
- Stable nuclear and atomic-charge ESP plus Experimental density-grid electronic ESP.
- Self-contained offline molecular workbench with measurements and scientific surfaces.
- Reproducible HTML/Markdown reports and publication-quality table and figure exporters.
- Complete MkDocs documentation website and permanent scientific validation registry.
- Cross-platform CI, distribution smoke testing, and dependency security auditing.

### Changed

- Replaced the oversized interactive landing page with a compact workflow palette.
- Added a functional `openwfn --version` command and preferred nested geometry interface.

### Known limitations

- Pure spherical d/f transformation and higher angular momenta remain Unsupported.
- Electronic and total ESP grid quadrature remain Experimental.
- Seven provenance-complete validation corpus cases remain explicitly pending.

## [0.6.1] - 2026-09-10

### Fixed

- Synchronized source, runtime, citation, and distribution versions.
- Added built-wheel installation verification.
- Clarified that Gaussian binary checkpoint conversion requires `formchk`.

## [0.6.0] - 2026-04-01

### Added

- Local standalone molecule viewer and polished interactive workflows.
