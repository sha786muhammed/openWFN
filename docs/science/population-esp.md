# Population analysis and electrostatic potential

## Mulliken populations

Mulliken analysis partitions the AO density using the overlap matrix. Atomic electron populations are accumulated from basis functions assigned to each atom, and charge is nuclear charge minus assigned electrons. Results can be strongly basis-set dependent.

## Symmetric Löwdin populations

Löwdin analysis first applies symmetric orthogonalization with $S^{1/2}$ before collecting atomic populations. It offers a different partition, not a uniquely “correct” atomic charge. Report the method and basis set whenever comparing charges.

## Electrostatic potential

At point $\mathbf r$, the nuclear term is

$$
V_\mathrm{nuc}(\mathbf r)=\sum_A\frac{Z_A}{\lVert\mathbf r-\mathbf R_A\rVert}.
$$

Charge-model potentials use Mulliken or Löwdin point charges. Grid-derived electronic potential approximates the Coulomb integral of the electron density, and total potential combines electronic and nuclear terms.

Never evaluate exactly at a nucleus, where the point-nuclear expression is singular. Coordinates and potential are interpreted in atomic units for this command.

## Interpretation and status

- Nuclear and Mulliken/Löwdin point-charge ESP: **Stable** implementation, subject to model limitations.
- Grid-derived electronic and total ESP: **Experimental**. Numerical Coulomb quadrature is sensitive to grid coverage and near-singular behavior.

Do not present different population schemes as experimentally observable charges. Use them as model-dependent descriptors and test whether conclusions survive reasonable methodological choices.


## Gaussian-integral point ESP

The development branch defaults electronic/total point ESP to `--method integrals`.
The shared Python entry point is `load(path).esp((x, y, z), component="total")`.
Coordinates are angstrom and the returned potential is hartree/e. The electronic
term is `-sum(P_mu,nu * V_mu,nu)`, using the total spin-summed AO density;
`V_mu,nu = integral chi_mu(r) chi_nu(r) / |r-C| dr`.

The native kernel uses the Laplace identity
`1/r = (2/sqrt(pi)) integral_0^infinity exp(-t*t*r*r) dt`, the Gaussian product
theorem, exact Cartesian polynomial moments and the change of variable
`u=t/sqrt(alpha+beta+t*t)`. The remaining integral is on `[0,1]`.
Normalization and pure spherical transforms are shared with the existing AO core.
Two Gauss–Legendre rules (64 and 96 nodes) check numerical consistency to
`1e-10 hartree/e`. This difference is a convergence diagnostic, not a rigorous
error bound. A rescaled interval resolves the far-field Gaussian tail.

Before integral evaluation, a primitive/node work estimate must remain below
100 million and a request may contain at most 1024 points. AO-metric electron
conservation must pass `1e-6 e`; unmet convergence/conservation returns partial
Experimental results. Nuclear/total ESP remains singular at a nucleus, whereas
purely electronic ESP is finite there. ECPs use source effective nuclear charges;
this reference corpus does not independently validate all ECP conventions.

Fresh PySCF `int1e_rinv` comparisons cover 11 restricted/unrestricted, charged,
diffuse and Cartesian/pure molecular cases at three points each (including a
nuclear center for the electronic term), with `1e-8 hartree/e` tolerance. Exact
radial expectations independently test every primitive Cartesian/pure s–h
component at its center. Successful integral results are **Validated** for this
scope. The earlier spatial-grid ESP remains available with `--method grid` and
remains Experimental, with its recorded convergence failures retained.

```bash
openwfn examples/everyday-qc/ammonium_cation.molden esp point 1.127 1.434 1.741 --method integrals
```

The structured result contains `method`, `value`, `electron_count`,
`expected_electrons`, `electron_conservation_error`, `quadrature_nodes`,
`quadrature_check_nodes`, `quadrature_max_error`, `quadrature_passed`, source
provenance, validation status and result status.
