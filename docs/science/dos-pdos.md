# Orbital-energy DOS and projected DOS

**Validation status: Validated for the documented everyday-QC reference scope.**

This is finite-molecule **orbital-energy** analysis, not periodic band structure and not an experimental photoelectron or excited-state spectrum. For source orbital energies `epsilon_i`, openWFN uses normalized Gaussian broadening:

`DOS(E) = sum_i exp[-(E-epsilon_i)^2/(2 sigma^2)] / (sigma sqrt(2 pi))`.

Each supplied spatial orbital counts once per source spin channel. Restricted orbitals are not doubled and occupation does not weight the DOS. Energy and `sigma` are in eV; DOS is in orbitals/eV. `sigma` is the Gaussian standard deviation, so `FWHM = 2 sqrt(2 ln 2) sigma`.

```bash
openwfn molecule.fchk orbitals dos --sigma 0.3 --export dos.csv
openwfn molecule.fchk orbitals dos --spin beta --sigma 0.2 --energy-min -20 --energy-max 10 --points 1501 --export dos.svg
openwfn --format json molecule.fchk orbitals dos
```

```python
from openwfn import load
record = load("molecule.fchk").dos(sigma_ev=0.3, spin="all")
```

Required input is an isolated calculation with orbital energies. The default range spans the supplied energies with five `sigma` of padding. Explicit ranges require both endpoints; the point count is bounded. Kernels are evaluated in bounded chunks and oversized requests fail before the large output allocation.

Results record the energy grid, per-source-channel arrays, total DOS, broadening, orbital count, numerical integral, and analytic truncated Gaussian area. Excessive range truncation, an under-resolved grid, or integral disagreement returns a partial result with an actionable warning. openWFN applies no automatic Fermi shift or correction of orbital energies.

CSV, JSON, PNG, and SVG exports reuse the same numerical result. Plotting does not recompute or silently modify the spectrum.

## Projected DOS

For group `g`,

`PDOS_g(E) = sum_i w_gi G_sigma(E-epsilon_i)`,

where `w_gi` comes from the named [Mulliken or Löwdin orbital-composition convention](orbital-composition.md). The default is Löwdin grouped by AO center. Element grouping combines centers of the same element; angular grouping partitions s/p/d/etc. SP shells are split into s and p. Mulliken projected weights can be negative and are not probabilities.

```bash
openwfn molecule.fchk orbitals pdos --group-by element --method lowdin --export pdos.svg
openwfn molecule.fchk orbitals pdos --group-by angular --sigma 0.2 --export pdos.csv
```

```python
result = load("molecule.fchk").pdos(group_by="element", method="lowdin")
```

PDOS additionally requires a supported AO basis, overlap, and MO coefficients. The raw MO norm and overlap conditioning are checked before interpretation. Output records include the projected series, grouping, projection convention, raw-norm diagnostics, overlap diagnostics, and `projection_sum_max_error`. Projection channels are checked against the total DOS point by point. Resource bounds limit the total number of projected output values before allocation.

Löwdin populations depend on AO representation. Equivalent real-space wavefunctions represented in differently normalized or contracted AO bases need not have identical Löwdin atom partitions. No basis-independent projection claim is made.

## Validation evidence

DOS is checked against analytic Gaussian peak, area, spin-counting, and truncation references. PDOS is checked for projection closure across atom, element, and angular groupings and both supported projection conventions.

The stable everyday-QC evidence independently reconstructs DOS and PDOS from the committed PySCF same-wavefunction references and compares them with openWFN for the documented RHF/UHF corpus. The report records input hashes, energy-rounding limitations, tolerances, dependency versions, and observed maximum errors in `validation/everyday-qc/pyscf-report.json`.

`validation/manifest.json` is the authoritative current status index. Validation here establishes correctness of the documented post-processing implementation for the named wavefunctions and controls; it does **not** establish physical accuracy of Hartree-Fock orbital energies, equivalence to a solid-state density of states, or equivalence to an experimental spectrum.
