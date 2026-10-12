# Scientific methods

Use this overview to understand the main calculations. Each linked method
page explains the required data, equations, units and validation limits.

## Geometry

Distances use Euclidean Cartesian separation. Angles use the normalized dot product. Dihedrals use a signed `atan2` convention. Coordinates are converted to ångströms at the parser boundary.

## Gaussian basis and density

Cartesian contracted Gaussian functions are evaluated with primitive and contraction normalization. The electron density is

$$
\rho(\mathbf r)=\sum_{\mu\nu}P_{\mu\nu}\phi_\mu(\mathbf r)\phi_\nu(\mathbf r).
$$

Alpha and beta matrices are derived from total and spin matrices as \(P^\alpha=(P+P^s)/2\) and \(P^\beta=(P-P^s)/2\).

## Population analysis

Mulliken AO populations are the diagonal elements of \(PS\). Symmetric Löwdin populations use the diagonal of \(S^{1/2}PS^{1/2}\). Atomic charge is nuclear charge minus the assigned electron population.

## ESP

Nuclear ESP is \(\sum_A Z_A/|\mathbf r-\mathbf R_A|\). Mulliken and Löwdin
point-charge potentials use their respective atomic charges. Electronic and
total point ESP use Gaussian Coulomb integrals by default, with validation for
the documented reference cases. The optional spatial-grid method remains
Experimental. See [Population and ESP](science/population-esp.md).
