# Mayer bond orders

**Validation status: Validated for the documented everyday-QC reference scope.**

For total AO density `P`, spin density `Q = P_alpha - P_beta`, and overlap `S`, openWFN uses the spin-corrected Mayer definition

`B_AB = sum_(mu in A,nu in B) [(PS)_mu,nu (PS)_nu,mu + (QS)_mu,nu (QS)_nu,mu]`.

For a restricted closed shell the spin term vanishes. For unrestricted calculations the same expression is evaluated from the source total and spin densities. The convention is documented explicitly because Mayer indices depend on the density and AO representation used.

## Requirements and safeguards

Required data are an isolated molecule, a supported Gaussian basis, total AO density, and analytical overlap. A confirmed restricted closed shell can derive `Q = 0`; an open-shell input without the required spin information does not silently invent it. Nonfinite, asymmetric, or dimensionally inconsistent matrices are rejected.

Post-HF inputs retain the density-source warning when the available matrix is the SCF density rather than a correlated density. Charge and spin conservation diagnostics are part of the result. A conservation failure produces a partial result and warning instead of a clean success.

The full matrix is symmetric, dimensionless, and reported with a zero diagonal. Public atom indices are **one-based**. The compact pair table includes entries satisfying `abs(B_AB) >= threshold`; filtering never changes the full matrix or row sums. Negative values are retained. `bonded_valence` is the unfiltered row sum and should be treated as a diagnostic, not as a formal oxidation state or universally integral bond count.

```bash
openwfn molecule.fchk bondorder mayer --threshold 0.1
openwfn molecule.fchk batch --analyses mayer --output-dir results
openwfn molecule.fchk report build report.html --analyses mayer
```

```python
from openwfn import load
record = load("molecule.fchk").mayer(threshold=0.1)
print(record.data["bond_order_matrix"])
```

Structured output includes `bond_order_matrix`, `pairs`, `bonded_valence`, `threshold`, `charge_conservation_error`, density-source fields, reference kind, and spin-conservation diagnostics.

## Validation evidence

The implementation is checked against analytic two-center cases, including a two-electron bond order of 1.0 and the corresponding one-alpha-electron case of 0.5. Independent cclib 1.8.1 Mayer contractions verify the restricted and unrestricted algebra. Cross-format water regressions verify the normalized input adapters.

For the stable everyday-QC scope, the committed RHF/UHF molecular corpus is compared against independently constructed same-wavefunction references. `validation/everyday-qc/pyscf-report.json` records the reference matrices, input hashes, dependency versions, and observed errors. `validation/manifest.json` is the authoritative source for the current capability status and evidence scope.

These checks validate openWFN's **post-processing implementation for the named wavefunctions**. They do not establish that Mayer bond order is basis-independent, that it reproduces every other program's population-analysis convention, or that any particular numerical value is an automatic chemical bond classification. Diffuse functions, non-idempotent/correlated densities, and unusual AO representations still require careful interpretation.
