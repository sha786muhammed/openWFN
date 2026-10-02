# Orbital-energy DOS and projected DOS (Experimental development)

This is finite-molecule orbital-energy analysis, not periodic bands or an
experimental photoelectron spectrum. For source orbital energies epsilon_i,

`DOS(E) = sum_i exp[-(E-epsilon_i)^2/(2 sigma^2)] / (sigma sqrt(2 pi))`.

Each supplied spatial orbital counts once per source spin channel. Restricted
orbitals are not doubled; occupation does not weight the DOS. Energy and sigma
are in eV, DOS in orbitals/eV. Sigma is a standard deviation, not FWHM;
`FWHM = 2 sqrt(2 ln 2) sigma`. Negative plotted orbital energies are legitimate.

```bash
openwfn molecule.fchk orbitals dos --sigma 0.3 --export dos.csv
openwfn molecule.fchk orbitals dos --spin beta --sigma 0.2 --energy-min -20 --energy-max 10 --points 1501 --export dos.svg
openwfn --format json molecule.fchk orbitals dos
```

```python
from openwfn import load
record = load('molecule.fchk').dos(sigma_ev=.3, spin='all')
from openwfn.exporters.spectra import write_spectrum
write_spectrum(record, 'dos.png', dpi=300)
```

Required: isolated calculation with orbital energies; the implementation uses
normalized orbital records and does not require AO overlap for total DOS.
Default range spans all supplied energies with five sigma of padding. Automatic
grid step is at most sigma/5. Explicit ranges require both endpoints; points
must be 2..100000. Kernels are evaluated in bounded chunks. A requested grid or
projection exceeding resource bounds fails before its kernel allocation.

The result records energy grid, per-source-channel arrays, total DOS, sigma,
orbital count, numerical integral and analytic truncated Gaussian area. Range
loss above 0.5%, step above sigma/3 or integral disagreement above 0.5% produces
partial status and an actionable warning. There is no automatic energy shift,
Fermi-level convention or correction of orbital energies. Interpret Kohn-Sham
orbital energies conservatively; the broadening is a visualization parameter.

JSON export preserves the complete ResultRecord. CSV has one energy row per
point and explicitly named channels, with energy in eV and DOS in orbitals/eV.
PNG/SVG use shared numerical results, 300 dpi by default, labeled axes and a
compact legend. SVG description metadata retains provenance/status/warnings.

Closed-form Gaussian normalization/peak checks, spin counting, truncation,
resource errors and interface parity provide limited validation evidence;
there is no independent molecular DOS reference capture yet. New methods stay
Experimental. Default read-only DOS is available through batch/reports/MCP.

DOS stage verification: 647 passed, 1 skipped; lint and strict documentation
build pass. Twelve DOS tests include analytic line shape/integral checks and
numerical CSV/SVG exports; default registry parity covers all five interfaces.

## Projected DOS

`PDOS_g(E) = sum_i w_gi G_sigma(E-epsilon_i)`, with weights from the named
[Mulliken/Löwdin composition convention](orbital-composition.md). Default
projection is Löwdin, grouped by AO center. `--group-by element` combines centers
with the same element; `--group-by angular` partitions s/p/d/etc. SP shells split
into s and p. Each supplied spin channel has separate `spin:group` series.
Mulliken projections can be negative and are not probabilities.

```bash
openwfn molecule.fchk orbitals pdos --group-by element --method lowdin --export pdos.svg
openwfn molecule.fchk orbitals pdos --group-by angular --sigma 0.2 --export pdos.csv
```

```python
result = load('molecule.fchk').pdos(group_by='element', method='lowdin')
```

Additional required data are supported AO basis, overlap and coefficients.
Raw MO norms and overlap conditioning are checked before interpretation; failed
norms yield partial status even though normalized projections conserve the
pointwise total. The output records `projections`, `group_by`,
`projection_method`, `max_raw_mo_norm_error`, overlap diagnostics and
`projection_sum_max_error`. All projection/spin series sum to total DOS to
1e-10 orbitals/eV in the named tests. Output is limited to two million projected
values across spin channels, before projected spectrum allocation.

Löwdin populations depend on the AO representation. Equivalent contracted and
uncontracted primitive wavefunctions need not give identical Löwdin atom
partitions, even when their real-space fields agree. Cross-format composition
comparisons must specify the same basis representation; no basis-independent
projection claim is made. Neither method is a unique real-space electron partition.

PDOS stage verification: 656 passed, 1 skipped; lint and strict docs pass.
Eight PDOS tests cover all six grouping/convention combinations, raw norm
failures and missing-data/invalid-parameter behavior. Additional cross-format
Mayer regressions are a separate adapter-fix stage.
