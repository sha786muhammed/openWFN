# Molecular orbitals and electron density

## Molecular orbitals

An orbital is expanded in atom-centered basis functions:

$$
\psi_p(\mathbf r)=\sum_\mu C_{\mu p}\phi_\mu(\mathbf r).
$$

Frontier analysis selects occupied and unoccupied orbital energies using the electron count and spin channel. HOMO–LUMO gaps are orbital-energy differences, not direct predictions of optical excitation energies.

## Density

For an AO density matrix $P$,

$$
\rho(\mathbf r)=\sum_{\mu\nu}P_{\mu\nu}\phi_\mu(\mathbf r)\phi_\nu(\mathbf r).
$$

For spin-resolved data, alpha and beta matrices can be derived from compatible total and spin matrices. The spin density is the alpha–beta difference.

## Numerical grids

openWFN evaluates density on a Cartesian bounding-box grid. `--spacing` controls point separation and `--padding` extends the box beyond the molecular coordinates, both in bohr. Finer spacing improves quadrature resolution but increases memory and runtime; larger padding captures diffuse tails.

Electron conservation is the principal numerical check:

$$
N_\mathrm{grid}\approx\int\rho(\mathbf r)\,d\mathbf r.
$$

Converge both spacing and padding for each chemical system. The active validation set does not establish universal accuracy.

**Status:** frontier analysis is Stable. Total-density integration and cube export are Validated only for the active provenance-backed cases. See the [validation matrix](validation-status.md).

