# Orbital composition

**Validation status: Validated for the documented everyday-QC reference scope.**

Required data are an isolated molecule, a supported Gaussian AO basis, MO coefficients, and overlap. For real coefficients `c` and overlap `S`, openWFN exposes two named projection conventions:

- **Mulliken:** `w_mu = c_mu (S c)_mu / (c^T S c)`.
- **Symmetric Löwdin:** `w_mu = [(S^1/2 c)_mu]^2 / (c^T S c)` (default).

The symmetric Löwdin square root is obtained from the AO-overlap eigensystem. Fractions are dimensionless; atom percentages are 100 times the atom fraction. AO-to-center and shell maps follow the normalized basis ordering. SP shells are split into s and p for angular grouping. Ghost centers retain their AO weights because this is a basis projection, not a unique real-space partition of electrons.

Mulliken contributions may be negative or exceed one. Do not clip them, treat them as probabilities, or reinterpret them as oxidation states. Löwdin contributions depend on the AO representation and therefore are not basis-representation invariant.

```bash
openwfn molecule.fchk orbitals composition --mo homo --method lowdin
openwfn molecule.fchk orbitals composition --mo 25 --spin beta --method mulliken
openwfn molecule.fchk batch --analyses orbital-composition --output-dir results
openwfn molecule.fchk report build report.html --analyses orbital-composition
```

```python
from openwfn import load
record = load("molecule.fchk").orbital_composition(mo="lumo", spin="alpha")
record = load("molecule.fchk").analyze(
    "orbital-composition", mo=25, method="mulliken"
)
```

Results include `method`, `mo_number`, `spin`, raw `ao_metric_norm`, normalized `ao_contributions`, `atom_contributions`, `shell_contributions`, `angular_contributions`, and `normalization_residual`. Each grouped partition is checked for closure. Raw norm disagreement above the documented tolerance and severe overlap conditioning produce partial results and warnings; an indefinite overlap or zero-norm MO fails explicitly. Normalizing fractions never turns an invalid source orbital into a valid one.

## Validation evidence

Analytic two-AO references verify the projection algebra, including signed Mulliken behavior and symmetric Löwdin partitioning. Cross-format regressions check equivalent wavefunction representations.

The stable everyday-QC evidence additionally compares molecular orbital compositions against independently calculated same-wavefunction PySCF references for the committed RHF/UHF corpus. Both Mulliken and Löwdin comparisons are made where AO normalization conventions permit a meaningful comparison; representation-dependent Cartesian Löwdin differences are recorded rather than forced into an equivalence claim. Input hashes, tolerances, dependency versions, and observed errors are preserved in `validation/everyday-qc/pyscf-report.json`.

`validation/manifest.json` is the authoritative source for the current capability status and scope. Validation here means that openWFN's named projection calculations reproduce the documented references for those wavefunctions; it does not make Mulliken or Löwdin population analysis a unique physical decomposition or guarantee equivalence across arbitrary AO representations, elements, ECPs, methods, or programs.
