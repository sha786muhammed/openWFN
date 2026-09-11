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

