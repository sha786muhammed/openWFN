# Orbital composition (Experimental)

Required: an isolated molecule, Gaussian AO basis, coefficients and overlap.
For real coefficients c and overlap S, openWFN reports two named definitions:

- Mulliken: `w_mu = c_mu (S c)_mu / (c^T S c)`.
- Symmetric Löwdin: `w_mu = [(S^1/2 c)_mu]^2 / (c^T S c)` (default).

The Löwdin square root uses the symmetric AO-overlap eigensystem. Fractions
are dimensionless; atom percentages are 100 times the atom fraction. The
AO-to-center and shell maps use the normalized basis ordering. SP shells are
split into s and p for angular grouping. Ghost centers retain their AO weights;
composition is a basis projection, not a unique spatial partition of electrons.
Mulliken weights may be negative or exceed one. Do not interpret them as
probabilities, clip them, or use them as oxidation states.

```bash
openwfn molecule.fchk orbitals composition --mo homo --method lowdin
openwfn molecule.fchk orbitals composition --mo 25 --spin beta --method mulliken
openwfn molecule.fchk batch --analyses orbital-composition --output-dir results
openwfn molecule.fchk report build report.html --analyses orbital-composition
```

```python
from openwfn import load
record = load('molecule.fchk').orbital_composition(mo='lumo', spin='alpha')
# Registry accepts the same keyword parameters:
record = load('molecule.fchk').analyze('orbital-composition', mo=25, method='mulliken')
```

Data include `method`, `mo_number`, `spin`, raw `ao_metric_norm`, normalized
`ao_contributions`, `atom_contributions`, `shell_contributions`,
`angular_contributions`, and `normalization_residual`. Each grouped partition
sums to one. Raw norm disagreement above 1e-6 and overlap minimum eigenvalue
below 1e-8/condition number above 1e10 produce partial results and warnings.
An indefinite overlap or zero-norm MO fails explicitly. Normalizing fractions
does not establish that the original orbital was valid.

Analytic two-center bonding references, negative Mulliken cases, raw-norm
regressions and interface parity establish limited evidence. Independent
molecular orbital-population comparisons remain required before promotion.
The mathematical conventions agree with the
[ORCA population documentation](https://orca-manual.mpi-muelheim.mpg.de/contents/spectroscopyproperties/population.html),
but this citation is not evidence that ORCA was run on these fixtures.
Default registered analyses are read-only and available in batch/reports/MCP;
the current batch/MCP interfaces use the documented default HOMO/alpha/Löwdin.

Stage verification: 626 passed, 1 skipped across the full implemented suite;
lint and strict documentation build pass. The planned Mayer tests were staged
separately and intentionally excluded until that method's implementation.
