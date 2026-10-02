# Molecular-orbital cubes

**Status: independently checked orbital fields; each generated cube retains its own grid-convergence status.**

For a real Gaussian AO basis, the signed field is

`psi_i(r) = sum_mu C_mu,i chi_mu(r)`

in `bohr^-3/2`. It is an orbital amplitude; its square is an orbital density. Overall MO phase has no physical significance. openWFN evaluates the source-normalized Cartesian or pure-spherical AO basis and applies recorded input-convention transforms where required.

Required data are isolated geometry, a supported Gaussian basis, and coefficients for the selected spin channel. Public orbital numbers are **one-based**. `alpha` uses the restricted channel on restricted inputs; requesting an unavailable beta channel fails explicitly. HOMO/LUMO selection follows the normalized occupations used by frontier analysis and HOMO selection remains usable when no virtual orbitals are present.

```bash
openwfn molecule.fchk orbitals cube --mo homo --output homo.cube
openwfn molecule.fchk orbitals cube --mo lumo --spin beta --output lumo-beta.cube --spacing 0.2 --padding 6
openwfn molecule.fchk orbitals cube --mo 25 --output mo25.cube
```

Spacing and padding are in **bohr**, matching density commands. The molecular grid is bounded before allocation and AO evaluation uses bounded chunks. Cube comments record MO selection, spin, spacing, padding, and input hash. Structured results retain parser provenance, orbital energy and occupation, grid shape, raw `ao_metric_norm = c^T S c`, and `squared_amplitude_integral`.

```python
from openwfn import load
result = load("molecule.fchk").orbital_cube(
    "homo.cube", mo="homo", spacing_bohr=0.2
)
print(result.as_dict())
```

Coefficients are never silently renormalized. A raw metric-norm error or a requested real-space grid that does not reproduce the expected squared-amplitude norm within the documented tolerance produces a warning and a partial result. Refine spacing and padding for quantitative use. A command successfully writing a cube does **not** imply that its chosen grid passed the convergence diagnostic.

## Validation evidence

Analytic normalized-Gaussian tests establish sign, amplitude, and squared norm. Independent GBasis comparisons verify mapped Cartesian and pure-d AO evaluations. Cross-format tests compare equivalent FCHK, Molden, MWFN, WFN, and WFX representations with global MO phase handled explicitly.

The stable everyday-QC reference suite additionally compares HOMO/LUMO fields against PySCF AO evaluations for the documented molecular cases and records serialized cube-value errors in `validation/everyday-qc/pyscf-report.json`. Those field comparisons validate the orbital evaluator for the stated scope.

The **cube result itself remains conditional on the requested grid**. Some deliberately coarse release-corpus cube settings produce `partial` normalization diagnostics even though the field values agree with the independent reference. openWFN preserves that distinction rather than promoting every written file to a clean validated result.

`validation/manifest.json` and the [everyday-QC validation page](../project/everyday-qc-validation.md) define the current evidence scope. The reference set does not establish arbitrary high-angular-momentum molecular coverage, ECP behavior, every program convention, or grid convergence for settings the user has not tested. Cube writing remains outside the read-only MCP interface.
