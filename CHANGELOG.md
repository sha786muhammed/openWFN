# Changelog

All notable changes to openWFN are documented in this file.

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
