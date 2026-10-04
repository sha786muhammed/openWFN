# Limitations

- Native FCHK remains the preferred source for full quantitative wavefunction
  analysis. The optional IOData 1.0.1 adapter can ingest the 25 listed
  formats, but the available analyses depend on the records in each file.
  Ingestion validation is fixture-scoped, not a claim of universal coverage
  across program versions or every job type.
- The cross-format water checks compare files derived from one originating
  FCHK calculation. They test conversion consistency, not independent
  scientific agreement with external calculations or experiment.
- ORCA, Q-Chem, and GAMESS output fixtures used in this branch are constructed
  program-output examples with geometry/energy fields; incomplete orbitals
  are not interpreted as a wavefunction. Broader native program coverage and
  independent reference corpora remain open work.
- Multi-record trajectories are not yet a sequence API: one record is loaded,
  and multi-frame XYZ is rejected rather than silently concatenated.
- Periodic cells, volumetric grids, and integral-only records can be ingested,
  but isolated-molecule frontier, population, and density analyses are not
  inferred from those components.
- Binary CHK files require Gaussian `formchk` and are not decoded internally.
- Gaussian real spherical 5D, 7F, 9G, and 11H shells are supported; pure spherical shells above H (`l > 5`) are rejected explicitly.
- ECP and ghost centers are handled with effective nuclear charges from the FCHK `Nuclear charges` record when present, and regression tests cover those semantics. This is source-faithful handling, not broad independent validation of every ECP family, basis set, or ghost-center workflow.
- Native Hirshfeld in the 0.11 development branch is validated only for ordinary neutral-pro-atom populations/charges on H/C/N/O all-electron wavefunctions in the named ten-case set. Elements outside H/C/N/O, ECP/pseudopotential cases, and ghost-center ambiguity are rejected rather than assigned guessed reference densities. Ordinary unrestricted Hirshfeld uses the total density; no spin-Hirshfeld definition is implied.
- Hirshfeld charges depend on numerical integration. The committed standard grid passed a fixed standard-to-fine gate on the ten validation cases, but users should still inspect returned diagnostics and converge the grid when extending beyond that evidence scope. Final charges are not rescaled to force charge closure.
- For post-HF calculations, openWFN currently warns when an analysis is using the available SCF density. A warning naming the SCF density does not mean a correlated/post-SCF density was parsed or selected; post-SCF density support should not be assumed.
- Density integration and cube validation depend on the numerical grid. The default **0.15 bohr** spacing is an accuracy/performance tradeoff and may be insufficient for tightly localized core density, heavy atoms, diffuse tails, or unusually demanding quantitative targets. Converge spacing and padding for the system being reported.
- Density-grid AO evaluation is chunked to limit peak memory, but the Cartesian point grid and final scalar values still occupy memory. Extremely large boxes or very fine grids can therefore remain expensive.
- Molecular-summary bonds and fragments are inferred with a covalent-radius heuristic. This may not represent unusual coordination, transition states, stretched bonds, metals, or other nonstandard bonding situations.
- Gaussian-integral electronic and total point ESP is Validated for the documented
  eleven-case reference set. The explicit grid-based electronic/total ESP
  quadrature pathway remains Experimental and requires system-specific convergence.
- Embedded coarse workbench grids are visualization data unless separately converged and validated; they are not final quantitative integration evidence.
- Independent `qc-iodata==1.0.1` comparisons currently cover parsed total energies and alpha frontier orbitals for six cases. They do not validate Mulliken, Löwdin, ESP, or density algorithms.
- Multiwfn same-wavefunction comparisons validate frontier orbitals, Mulliken charges, and Löwdin charges only for restricted water and unrestricted LiH; broader chemical coverage remains pending.
- Synthetic/special-case regression fixtures for ECP, ghost, UHF, ROHF, and post-HF behavior protect implementation contracts but are not a substitute for an independently reproduced validation corpus.
- XYZ files provide geometry only.
- Structure-only and periodic summaries are partial by design: missing
  effective charges, electron counts, orbitals, and energies are not guessed.
  A known zero effective nuclear charge identifies a ghost center; an absent
  charge remains unknown. XYZ/PDB/MOL/SDF exports cannot retain ghost/ECP
  effective charges and emit explicit loss warnings.
- Batch processing accounts for supported, partial, failed, and unsupported
  discovered inputs. An unsupported file makes the top-level batch fail, even
  if other files succeed. Format hints help with ambiguous filenames; they
  cannot make a damaged or unrecognized scientific record valid.

Always record the openWFN version, source-file checksum, grid settings, units,
warnings, execution status, and validation status in research outputs.

## Everyday-QC validation scope

MO cube fields, orbital composition, Mayer, DOS and PDOS have the documented
0.10-series validation boundaries. Native ordinary Hirshfeld on the 0.11
development branch is **Validated** for the named ten-case H/C/N/O all-electron
scope using committed independent HORTON-PART comparison and openWFN grid-
refinement evidence. None of these scoped claims is universal validation across
all elements, high angular momentum, ECPs, correlated densities or programs.
Löwdin partitions depend on AO representation; Mulliken fractions/PDOS may be
signed. Mayer row sums are bonded-valence diagnostics, and correlated improved
Mayer definitions are absent. DOS is finite-molecule orbital-energy broadening
with one count per supplied spatial orbital/channel, without occupancy weighting
or periodic bands. Failed source, conditioning, normalization or convergence
diagnostics remain failed or partial/Experimental.

Typed spectroscopy/NTO and real-space topology/basin methods are not yet
implemented. See the [completion and gate record](project/everyday-qc-validation.md).
