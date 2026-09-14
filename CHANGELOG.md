# Changelog

All notable changes to openWFN are documented in this file.

## [0.8.0a1] - 2026-09-14

### Added

- Added a versioned calculation boundary with schema `2.0`, immutable source identity, parser provenance, named transformations, and canonical source-format tracking.
- Added a versioned analysis registry and result envelope carrying analysis identity, units, validation status, warnings, timing, provenance, and structured failures.
- Added multi-analysis batch manifests, recursive directory discovery, deterministic CSV indexing, and crash-safe resume from persisted result envelopes.

### Changed

- Unified named analysis execution across the Python API and high-throughput batch workflows.
- Redesigned the documentation website around task-oriented learning, CLI/API reference material, scientific-method documentation, and a single project identity.
- Added dedicated documentation integration testing without expanding the standard Python-version test matrix.

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
