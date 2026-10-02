# Mayer bond orders (Experimental)

For total AO density P, spin density Q=Palpha-Pbeta and overlap S:

`B_AB = sum_(mu in A,nu in B) [(PS)_mu,nu (PS)_nu,mu + (QS)_mu,nu (QS)_nu,mu]`.

This is the conventional spin-corrected Mayer definition for real AOs.
It reduces to the PS term for a restricted closed-shell density and to twice
the sum of the alpha and beta density products for unrestricted calculations.
Definitions are described in the
[ORCA population manual](https://orca-manual.mpi-muelheim.mpg.de/contents/spectroscopyproperties/population.html).

Required: isolated molecule, supported Gaussian basis, total AO density and
analytical overlap. A confirmed restricted closed shell can derive Q=0;
open-shell files missing spin density fail. The shared density-channel helper
controls this decision. Asymmetric/mismatched/nonfinite matrices are rejected.
SCF density in post-HF files retains the existing source warning. Correlated
spin/total source mismatches also produce a partial result. Improved correlated
Mayer indices are not implemented.

The matrix is symmetric, dimensionless and has zero diagonal (only atom-pair
orders are reported). Pair and atom indices are **one-based**. The compact pair
table includes `abs(B_AB) >= threshold`; filtering never alters the full matrix
or row sums. Negative values are retained, not clipped. `bonded_valence` is the
unfiltered row sum, a diagnostic rather than a formal oxidation state, total
valence or universally integral chemical bond count. Basis/diffuse-function
sensitivity and non-idempotent densities limit interpretation.

```bash
openwfn molecule.fchk bondorder mayer --threshold 0.1
openwfn molecule.fchk batch --analyses mayer --output-dir results
openwfn molecule.fchk report build report.html --analyses mayer
```

```python
from openwfn import load
record = load('molecule.fchk').mayer(threshold=.1)
print(record.data['bond_order_matrix'])
```

Structured data contain `bond_order_matrix`, `pairs`, `bonded_valence`,
`threshold`, `charge_conservation_error`, density sources and reference kind.
Charge conservation uses the existing Mulliken diagnostics and propagates
partial status. Analytic two-center tests give 1.0 for a two-electron bonding
orbital and 0.5 for the corresponding one-alpha-electron case; separate
spin-channel algebra verifies the factor of two. CLI/API/batch/report/MCP
compare identical default values. These do not establish accuracy for every
molecule or a comparison with a running ORCA installation.

Additional independent comparison: cclib 1.8.1 `MBO` constructs occupied
densities from the same synthetic two-center orbitals and agrees for restricted
and unrestricted cases to 1e-12. This isolates contraction/spin factors: the
source orbitals and overlap input are shared, so it does not validate their
parsing or overlap evaluation independently.

Stage verification: 634 passed, 1 skipped; lint and strict documentation build
passed. Seven Mayer tests include the two independent cclib contractions.

Cross-format adapter verification now includes equivalent water in Molden,
MWFN, WFN and WFX (2e-7 matrix tolerance). IOData restricted occupations retain
the source alpha/beta difference as a spin matrix, including nonzero ROHF spin.
The optional packaged LiH-cation ROHF/UHF fixtures verify integrated spin against
source occupations (2e-7 electrons). These comparisons share source wavefunctions
and are regression evidence, not new independently executed ORCA/Multiwfn captures.

Review hardening: `trace(Q S)` is compared against authoritative source
alpha-minus-beta electron counts or explicit unrestricted occupations. A spin
error above 1e-6 electrons produces partial status and a warning; an unavailable
spin expectation is also partial. Results expose `spin_electron_count`,
`expected_spin_electrons` and `spin_conservation_error`. This check catches
inflated spin matrices even when their reported density source matches.
