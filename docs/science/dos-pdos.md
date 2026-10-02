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
