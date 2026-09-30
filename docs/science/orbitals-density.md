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

For spin-resolved calculations, check alpha and beta integrals separately as well as their difference. In an exploratory Linux run of the [IOData O₂ UHF WFN fixture](https://github.com/theochem/iodata/blob/9f7e800fc414b086d677b5f2882dd0c1dfa919f3/iodata/test/data/o2_uhf.wfn), a grid with 0.20 bohr spacing and 4.0 bohr padding integrated 9.03171659 alpha and 7.03163594 beta electrons, versus occupation counts of 9 and 7. Their difference was 2.00008065 versus 2 expected: the small spin error partly reflects cancellation of larger channel errors. The input SHA-256 was `5405b851afbe7d55347a5c4ece0bfca2b9bbc1508e9374129693e0ed46aebb96`. This is a grid-convergence illustration, not an independent validation benchmark.

**Status:** frontier analysis is Stable. Total-density integration and cube export are Validated only for the active provenance-backed cases. See the [validation matrix](validation-status.md).
