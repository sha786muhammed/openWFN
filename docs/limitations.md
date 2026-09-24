# Limitations

- Gaussian-centered support is the v0.7 scientific scope; ORCA, Q-Chem, and Psi4 are future parser work.
- Binary CHK files require Gaussian `formchk` and are not decoded internally.
- Gaussian real spherical 5D, 7F, 9G, and 11H shells are supported; pure spherical shells above H (`l > 5`) are rejected explicitly.
- Electronic and total ESP use grid quadrature and are Experimental.
- Embedded coarse workbench grids are visualization data unless separately converged and validated; they are not final quantitative integration evidence.
- Independent `qc-iodata==1.0.1` comparisons currently cover parsed total energies and alpha frontier orbitals for six cases. They do not validate Mulliken, Löwdin, ESP, or density algorithms.
- Multiwfn same-wavefunction comparisons validate frontier orbitals, Mulliken charges, and Löwdin charges only for restricted water and unrestricted LiH; broader chemical coverage remains pending.
- XYZ files provide geometry only.

Always record the openWFN version, source-file checksum, grid spacing, padding, units, and validation status in research outputs.
