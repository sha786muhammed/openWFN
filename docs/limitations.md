# Limitations

- Full quantitative wavefunction analysis is currently Gaussian FCHK-centered.
  Native ORCA, Q-Chem, and Psi4 wavefunction inputs are unsupported.
- Binary CHK files require Gaussian `formchk` and are not decoded internally.
- Gaussian real spherical 5D, 7F, 9G, and 11H shells are supported; pure spherical shells above H (`l > 5`) are rejected explicitly.
- ECP and ghost centers are handled with effective nuclear charges from the FCHK `Nuclear charges` record when present, and regression tests cover those semantics. This is source-faithful handling, not broad independent validation of every ECP family, basis set, or ghost-center workflow.
- For post-HF calculations, openWFN currently warns when an analysis is using the available SCF density. A warning naming the SCF density does not mean a correlated/post-SCF density was parsed or selected; post-SCF density support should not be assumed.
- Density integration and cube validation depend on the numerical grid. The default **0.15 bohr** spacing is an accuracy/performance tradeoff and may be insufficient for tightly localized core density, heavy atoms, diffuse tails, or unusually demanding quantitative targets. Converge spacing and padding for the system being reported.
- Density-grid AO evaluation is chunked to limit peak memory, but the Cartesian point grid and final scalar values still occupy memory. Extremely large boxes or very fine grids can therefore remain expensive.
- Molecular-summary bonds and fragments are inferred with a covalent-radius heuristic. This may not represent unusual coordination, transition states, stretched bonds, metals, or other nonstandard bonding situations.
- Electronic and total ESP use grid quadrature and are Experimental.
- Embedded coarse workbench grids are visualization data unless separately converged and validated; they are not final quantitative integration evidence.
- Independent `qc-iodata==1.0.1` comparisons currently cover parsed total energies and alpha frontier orbitals for six cases. They do not validate Mulliken, Löwdin, ESP, or density algorithms.
- Multiwfn same-wavefunction comparisons validate frontier orbitals, Mulliken charges, and Löwdin charges only for restricted water and unrestricted LiH; broader chemical coverage remains pending.
- Synthetic/special-case regression fixtures for ECP, ghost, UHF, ROHF, and post-HF behavior protect implementation contracts but are not a substitute for an independently reproduced validation corpus.
- XYZ files provide geometry only.

Always record the openWFN version, source-file checksum, grid spacing, padding, units, warnings, execution status, and validation status in research outputs.