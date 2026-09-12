# Limitations

- Gaussian-centered support is the v0.7 scientific scope; ORCA, Q-Chem, and Psi4 are future parser work.
- Binary CHK files require Gaussian `formchk` and are not decoded internally.
- Gaussian real spherical 5D, 7F, 9G, and 11H shells are supported; pure spherical shells above H (`l > 5`) are rejected explicitly.
- Electronic and total ESP use grid quadrature and are Experimental.
- Coarse workbench grids are intended for visualization, not final quantitative integration.
- XYZ files provide geometry only.

Always record the openWFN version, source-file checksum, grid spacing, padding, units, and validation status in research outputs.
