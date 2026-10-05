# NCI and reduced density gradient

openWFN provides an **Experimental** total-density noncovalent-interaction (NCI)
analysis based on the reduced density gradient (RDG) and the second eigenvalue
of the electron-density Hessian. The implementation is designed to expose the
raw numerical fields and their validity diagnostics without inventing automatic
interaction labels, scientific cutoffs, or basin properties.

## Definitions

For total electron density \(\rho(\mathbf r)\), the reduced density gradient is

\[
s(\mathbf r)=\frac{|\nabla\rho(\mathbf r)|}
{2(3\pi^2)^{1/3}\rho(\mathbf r)^{4/3}}.
\]

The Cartesian density Hessian is symmetrized only after checking the maximum
antisymmetric residual against the declared numerical tolerance. Its eigenvalues
are ordered algebraically,

\[
\lambda_1 \le \lambda_2 \le \lambda_3.
\]

The signed-density field is

\[
\operatorname{sign}(\lambda_2)\rho.
\]

An exactly zero \(\lambda_2\) therefore gives a signed density of zero. Near-zero
\(\lambda_2\) values are retained but flagged as sign-ambiguous rather than
being forced into an attractive/repulsive interpretation.

## Numerical safeguards

The default density floor is `1.0e-12 electron/bohr^3`. It is a **numerical
safeguard**, not an NCI interaction cutoff. At point-analysis locations where
`rho <= density_floor`, RDG is invalid and is serialized as JSON `null`.

The default Hessian antisymmetry tolerance is
`1.0e-10 electron/bohr^5`. Materially nonsymmetric Hessians invalidate only the
Hessian-derived fields (`lambda2`, eigenvalues, and signed density). They do not
erase an otherwise valid RDG value, because RDG depends only on density and its
gradient.

The default lambda2 ambiguity threshold is the larger of
`1.0e-12 electron/bohr^5` and
`1.0e-10 * max(abs(lambda1), abs(lambda2), abs(lambda3))`. Ambiguity is an
interpretive warning and does not by itself make the numerical result partial.

Nonfinite density/derivative data are never emitted as NaN/Infinity in the
structured point result. Invalid numerical fields are serialized as `null` with
explicit masks and diagnostic counts.

## Point analysis

Pointwise NCI is available through the registered Python analysis:

```python
from openwfn import load

calc = load("water.fchk")
result = calc.analyze(
    "nci",
    points_bohr=[
        [0.0, 0.0, 1.0],
        [0.0, 0.0, 2.0],
    ],
)

print(result.data["rdg"])
print(result.data["lambda2"])
print(result.data["signed_density"])
```

The result kind is `nci_rdg`. It reports:

- `rho` in `electron/bohr^3`;
- density-gradient norm in `electron/bohr^4`;
- dimensionless RDG;
- ordered Hessian eigenvalues and `lambda2` in `electron/bohr^5`;
- `sign(lambda2)*rho` in `electron/bohr^3`;
- separate RDG and complete-field validity information;
- lambda2-sign ambiguity information;
- Hessian antisymmetry residuals;
- density source, thresholds, formulas, conventions, and diagnostics.

NCI uses **total density only**. openWFN does not define a spin-resolved NCI
variant in this release. If a post-HF calculation is represented only by an SCF
density, the result identifies that density source and warns rather than implying
that a correlated density was used.

## Cube export

The high-level Python API can export four scalar fields:

```python
calc.nci_cube("rho.cube", field="rho")
calc.nci_cube("lambda2.cube", field="lambda2")
calc.nci_cube("signed.cube", field="signed_density")
calc.nci_cube("rdg.cube", field="rdg", rdg_cap=2.0)
```

The equivalent CLI form is:

```bash
openwfn water.fchk nci cube signed.cube --field signed-density
openwfn water.fchk nci cube rdg.cube --field rdg --rdg-cap 2.0
```

`--spacing`, `--padding`, `--density-floor`, and `--chunk-size` are explicit
controls. Global `--overwrite` follows the normal openWFN file-writing policy.

RDG cube export requires an explicit positive finite `rdg_cap`; there is no
scientific default. The cap is a presentation/export bound, not an interaction
criterion. Valid RDG values above the cap are clipped and counted. Only
low-density-tail RDG values (`rho <= density_floor` with otherwise finite
inputs) may be replaced by the cap. Any other invalid/nonfinite RDG value aborts
the export. `rho`, `lambda2`, and signed-density exports never accept an
`rdg_cap`.

Cube generation uses the shared grid-point ceiling, AO memory budgeting,
chunking, and atomic cube writer. A final cube is not published if field
validation fails.

## Independent reference evidence

The required CI test `tests/validation/test_nci_pyscf_reference.py` regenerates
fresh PySCF 2.12.1 wavefunctions and independently reconstructs density,
density gradient, the full Cartesian density Hessian, ordered Hessian
eigenvalues, `lambda2`, RDG, and signed density from PySCF AO derivatives and
density matrices.

The named reference set includes:

- restricted water / STO-3G;
- Cartesian-basis water / 6-31G*;
- charged ammonium / 6-31G*;
- a hydrogen-bonded water dimer / 6-31G*, including intermolecular points;
- triplet O2 UHF / 6-31G* using total `D_alpha + D_beta` density.

Independent finite-difference checks at water and water-dimer points guard the
AO derivative/Hessian component ordering used by the reference calculation.
The test does not call the openWFN NCI numerical kernel to construct reference
values.

This evidence is meaningful for the named same-wavefunction HF cases, but it is
not universal validation. The public status therefore remains **Experimental**.

## Current exclusions

This implementation does not provide automatic NCI interaction labels,
automatic RDG/density visualization thresholds, promolecular NCI, periodic NCI,
NCI energies, basin integration, zero-flux basins, HTML/Workbench isosurfaces,
or a claim of exhaustive interaction discovery. ECP/pseudopotential systems,
complex-orbital cases, correlated/post-SCF density definitions, broader
high-angular-momentum coverage, and arbitrary producer/version combinations
still require dedicated validation evidence.
