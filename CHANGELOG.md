# Changelog

All notable changes to openWFN are documented in this file.

## [0.12.0] - Unreleased

- Use the selected pixel wordmark across interactive terminal screens, README, documentation, browser icon and offline HTML exports. The browser icon uses the matching W initial.
- Add file-free, labelled scientific conversation, session-only connection/model controls, editable input and cancellation back to the prompt. Supported short file-property requests work without a model. Model explanations are not independently verified scientific results.

- Route explicit short orbital/metadata chat questions directly to scientific tools, avoiding model latency and unnecessary restricted-spin prompts. Distinguish model timeouts from connection failures and show waiting progress on stderr.
- Render missing report values as "Not available" and show labelled, one-based atom/element population tables in HTML and Markdown without changing raw JSON values, units, provenance or scientific status.

- Include IOData, cclib and local MCP in the normal installation; retain existing extra names for compatibility. Model weights and Gaussian utilities are not bundled.
- Add capability-aware guided entry and a bounded `analyze` overview. Use explicit `summary` for the existing summary-only schema in scripts.
- Add local scientific chat with constrained tool plans, capability checks, fixed engine explanations, input-change detection, explicit remote permission and confirmed density settings. Models cannot supply scientific values or shell commands.
- Share file, AO, grid and parameter limits across chat and read-only MCP; expose density integration and one-point real-space analyses without file writes.
- Preserve unknown structure-only charge/spin, correct MOL/SDF property-charge precedence, and prevent rendered results from replacing input aliases. Publish exports atomically so failed writes preserve earlier files.
- Add editable guided settings, reproducible commands, JSON/CSV saving and tested keyboard navigation. Keep numerical algorithms and existing scientific validation boundaries unchanged.
- Remove archived internal planning documents, simplify user documentation and keep release history separate from onboarding.
- Include the existing main-branch Experimental QTAIM critical-point, ELF/LOL and NCI tools. No QTAIM basin integration or new validation promotion is included.

Release preparation only. No tag or publication is implied by this entry.

## [0.11.0] - 2026-10-04

Stable feature release integrating native Hirshfeld analysis, vibrational spectroscopy, and method-general excited-state/UV–Vis post-processing through the shared openWFN model and interfaces.

- Add ordinary neutral-pro-atom Hirshfeld populations and charges with permanent PySCF-generated H/C/N/O reference data, explicit unsupported ECP/ghost/element handling, closure diagnostics, and independent HORTON-PART validation for the named ten-case all-electron scope.
- Add native Gaussian harmonic vibrational records, IR intensities, Raman activities, normal-mode vectors, deterministic Gaussian broadening, CLI/Python/MCP parity, reports, exports, and an offline Workbench Vibrations workspace. Scientific status remains Experimental pending independent external spectroscopy validation.
- Add typed excited-state/job-block records and source-faithful Gaussian, ORCA, and Q-Chem adapters with multi-job isolation, method/amplitude-convention classification, transition dipoles, and conservative missing-data handling.
- Add UV–Vis stick/broadened profiles in energy space with the documented 0.20 eV default FWHM, dark-state preservation, invalid/missing oscillator-strength exclusions, and correct energy-to-wavelength Jacobian handling. Excited-state/UV–Vis scientific status remains Experimental pending named independent cross-program validation.
- Extend CSV/JSON/PNG/SVG export, HTML reports, Python analysis registry, local MCP routing, CLI commands, and offline Workbench integration without duplicating scientific engines across interfaces.
- Expand the bounded release resource benchmark to 110 prescribed workflows across eleven installed molecular examples and retain exact-commit CI, installed-wheel verification, PyPI trusted publishing, and post-publication public-PyPI reinstall verification.
- Preserve capability-specific validation labels: stable package status does not promote Experimental analyses to Validated.

## [0.10.1] - 2026-10-02

Release-evidence and published-package reproducibility hardening for the 0.10 stable line.

- Keep scientific numerical kernels, schemas and validation tolerances unchanged.
- Replace stale development-state validation prose with a current-state evidence page and extend the canonical validation manifest with current capability status and explicit historical-capture roles.
- Package the complete eleven-molecule everyday-QC corpus so installed wheels can reproduce the bounded real-workflow matrix without a repository checkout.
- Make the resource benchmark consume an explicit corpus, reject incomplete corpora, and record hashes for the actually imported package.
- Distinguish 99/99 prescribed command/resource completion from scientific validation status.
- Make the stable publication path version-driven and rerun the complete installed-corpus benchmark after downloading the exact release from public PyPI with interoperability/resource extras.

## [0.10.0] - 2026-10-02

Stable package release for the documented everyday QC and automation scope.

- Promote the tested 0.10.0rc1 implementation without changing scientific
  algorithms, schemas, numerical controls or individual validation labels.
- Retain the candidate's MO cubes/composition, Mayer, DOS/PDOS, native point ESP,
  interface parity and resource safeguards described below.
- Align version, citation, installation, support policy and release notes.
- Publish only after exact-commit CI, distribution and installed-wheel checks;
  verify installation and the water workflow from public PyPI.
- Allow fifteen minutes for browser CI including Chromium dependency setup.
  Native Hirshfeld and later spectroscopy/real-space phases remain unshipped.

## [0.10.0rc1] - 2026-10-02

Release candidate; 0.9.2 remains the stable release.

- Add signed MO cubes, documented Mulliken/Löwdin compositions, spin-corrected
  Mayer orders, Gaussian orbital-energy DOS and projected DOS through the common core.
- Add native Gaussian-integral point ESP with independent s–h and real-molecule evidence.
- Validate the everyday QC methods for eleven molecular wavefunctions; preserve
  failed/partial Experimental diagnostics and all unavailable-data safeguards.
- Stabilize tested local MCP, guided terminal and offline Chromium interfaces.
- Reduce grid/AO temporary memory and stream atomic cube exports.
- Add trusted-workflow deadline/RSS/storage checks and 99-workflow resource evidence.
- Publish an opt-in candidate after exact-commit CI, metadata, distributions and
  installed-wheel checks. Retain the later scientific implementation gates.

## [0.9.2] - 2026-10-01

### Fixed

- Structure-only summaries retain element composition and atom counts when effective nuclear charges are absent, without inventing electron counts or ghost/ECP classification.
- Human-readable CLI output separates analysis validation, result status, and source-job termination. FCHK inputs explicitly leave source convergence unknown.
- Point ESP reports specific singularity errors; zero-charge ghost centers no longer create a spurious nuclear singularity.
- Human-readable output properties abbreviate long arrays while keeping diagnostics and warnings. `--verbose`, JSON, CSV, and the Python API retain full values.

## [0.9.1] - 2026-10-01

### Fixed

- Grid analyses reject nonfinite settings and grids above two million points before allocation. Density AO chunks are also limited by basis size; spacing is never silently changed.
- Molden ingestion recognizes `.molden.input` and bounded `[Molden Format]` header detection for otherwise unrecognized filenames.
- Atomic-charge ESP preserves population conservation warnings and partial status.
- Research reports display warnings and partial result status; workbench fields retain those facts, ghost-center identity, and usable HOMOs when a LUMO is absent.
- Structure writers explicitly warn about molecular-charge and spin-multiplicity loss.
- Python geometry measurements accept isolated structure coordinates without requiring a complete wavefunction.

## [0.9.0] - 2026-10-01

### Added

- Optional IOData 1.0.1 ingestion with a pinned 25-format fixture contract and file-specific capability discovery.
- Canonical `OpenWFNData` components for structure, isolated calculations, periodic cells, volumetric grids, integrals, and metadata.
- Explicit CLI/API format hints and mixed-batch format maps; discovered unsupported inputs receive records rather than disappearing from results.
- Experimental source-reported output extraction through `read_output()` and the `properties` CLI command, using optional cclib 1.8.1.
- Experimental local stdio MCP tools for capability inspection, registered analyses, and output properties, using optional MCP SDK 2.2.0.

### Changed and fixed

- `load(...).data` now exposes `OpenWFNData`; direct access to the isolated molecular calculation moves to `.data.calculation`. Existing high-level analysis methods remain the recommended interface.
- Structure-only summaries return partial results without inferring electronic properties. Ghost and effective nuclear charges are retained where the source provides them.
- Structure exports warn when their destination format cannot retain ghost/ECP effective charges.
- CLI JSON failures and quiet-mode results use structured envelopes. Batch routing, failure reporting, and resume checks retain input identity and effective format hints.
- Expected open-shell density electron counts can use explicit orbital occupations when source electron-count records are unavailable.
- MCP rejects binary `.chk` files to avoid automatic conversion and file writes. Convert them outside MCP and supply `.fchk` instead.
- Archived internal planning documents are removed from the current documentation tree. Git history is unchanged.

### Evidence and boundaries

- Local verification recorded 570 passing tests and two skips with the optional interfaces installed. PR and post-merge CI passed Python 3.10–3.13, macOS/Windows smoke checks, interoperability, scientific validation, package checks, and optional-interface tests.
- Five water representations check conversion consistency from one originating calculation, not independent validation across arbitrary programs and molecules.
- Selected real ORCA, Q-Chem, and Gaussian outputs were compared with source values; a Gaussian CASSCF example retained a missing SCF energy rather than substituting another energy.
- Ingestion support does not imply a complete wavefunction or availability of every analysis. MCP and source-reported output extraction remain Experimental. General correlated-density and periodic electronic analysis are not claimed.
- Release metadata identifies version 0.9.0 and date 2026-10-01. No paper, DOI, or affiliation is claimed.

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
- Release smoke testing now verifies summary, frontier-orbital, report, and offline workbench workflows from the built wheel.

### Fixed

- Deferred Matplotlib imports until a plotting command runs, avoiding plotting startup work for ordinary CLI commands.
