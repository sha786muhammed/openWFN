# Choose a calculation and keep its evidence

Start with `openwfn FILE capabilities`, then `openwfn FILE open`. Availability
depends on records in the file, not just its extension. Use the guided method
families to configure a calculation. Missing records are an explanation, not a
numerical result. No interface should infer them.

## What each family needs

| Calculation | Required data | Main settings and checks |
| --- | --- | --- |
| Summary, geometry, fragments | Atomic structure; electronic metadata where available | One-based atom numbers, angstrom/degrees; inferred bonds are labelled as a radius heuristic |
| HOMO/LUMO | Orbital energies and occupations | Channel; fractional occupations or missing virtual orbitals remain explicit |
| Orbital composition | Basis, orbitals and AO overlap | HOMO/LUMO or one-based MO; Mulliken/Löwdin convention; normalization residual |
| MO cube | Same orbital records | Channel, MO, spacing/padding in bohr; signed amplitude is not density |
| DOS/PDOS | Orbital energies; PDOS also needs overlap and projections | Gaussian sigma in eV, energy range, point count, channel and grouping; truncated ranges can be partial |
| Mulliken/Löwdin | Density, basis and overlap | Electron/charge conservation; ill-conditioned overlap warnings |
| Hirshfeld | Density and supported neutral atomic references | Quadrature resolution/extent and convergence; current reference library is H/C/N/O, without ECP/ghost support |
| Mayer bond orders | Total/spin density, basis and overlap | Display threshold; symmetry and spin/charge closure; geometric bond detection is a different operation |
| Density integration/cube | Density and basis | Component, spacing/padding in bohr; refine the grid, retain partial conservation results and resource limits |
| ESP | Nuclear charges and electronic density for total/electronic ESP | Coordinates in angstrom, component and integral/grid method; nuclear singularities and ECP limits remain explicit |
| Frequencies, IR, Raman | Frequencies plus intensities/activities; vectors for a normal mode | One-based mode, FWHM in cm⁻¹, curve range/points; imaginary modes retained, Raman activity is not an experimental intensity |
| Excited states, UV–Vis | Excitation energies, strengths and job identity | One-based state/job, FWHM in eV, range/points; orbital gap is not an optical excitation |
| NTO | Compatible orbitals and complete supported transition amplitudes | One-based state/job; a list of excitation energies alone is insufficient |
| Derivatives/KED | Density, basis and supported analytic derivatives | Points in bohr, density component; units distinguish gradient, Hessian, Laplacian and KED |
| ELF/LOL | The same wavefunction fields | Explicit channel; open-shell total-channel definitions are not substituted; undefined-point masks retained |
| NCI/RDG | Density gradient and Hessian | Points or bounded cube; density floor and ambiguous Hessian signs remain explicit |
| QTAIM | Density gradient and Hessian | Seeds, iteration limits, bounded paths; finite search is not exhaustive topology or basin integration |
| Stored grids | A parsed grid and its recorded units | Inspect stored values; field identity is not proved by a `.cube` suffix |
| Source-output properties | Recognized QC output | Extracted, not recomputed; termination/convergence and unavailable values remain visible |

## A larger wavefunction example

From the repository root:

```bash
wf=examples/research-workflows/biphenyl/biphenyl.molden
openwfn "$wf" capabilities
openwfn "$wf" geometry distance 1 12
openwfn "$wf" orbitals frontier --spin all
openwfn "$wf" orbitals composition --mo homo --method lowdin
openwfn "$wf" population mulliken
openwfn "$wf" population lowdin
openwfn "$wf" population hirshfeld
openwfn "$wf" bondorder mayer --threshold 0.05
openwfn "$wf" orbitals dos --energy-min -30 --energy-max 30 --points 401
openwfn "$wf" orbitals pdos --group-by element --method lowdin \
  --energy-min -30 --energy-max 30 --points 401
openwfn "$wf" esp point 0 0 3 --component total --method integrals
openwfn --format json --output biphenyl-frontier.json \
  "$wf" orbitals frontier --spin all
```

The restricted energy window excludes core orbitals: inspect its warning rather
than treating it as a complete DOS. This Molden file has no frequency/excitation
records. Use [the pinned spectroscopy outputs](spectroscopy/README.md) for those
workflows, or your own frequency/TD output after checking capabilities.

Density and cube exports can cost much more than point properties. Start with
a coarse grid, compare finer spacings, and keep the safety limit. A coarse result
may be partial; do not label it converged because the command finished.

```bash
openwfn "$wf" density integrate --spacing 0.30 --padding 4
openwfn "$wf" orbitals cube --mo homo --spacing 0.30 --padding 4 \
  --output biphenyl-homo.cube
openwfn "$wf" report build biphenyl-report.html \
  --analyses summary,frontier,mulliken,lowdin
```

Use new output names. Existing files require explicit replacement permission.
Reports/workbench are exports, not independent reference calculations.

## Points, spectra and unavailable data

The guided **All calculation methods and requirements** route exposes registered
point-field, NTO and QTAIM methods as well as orbital and spectrum settings.
Some of these methods do not have a specialized direct CLI subcommand; Python
and MCP keep their structured records. See [the real-space example](real-space/README.md)
for reproducible point fields and QTAIM seeds.

For frequency data, guided IR/Raman controls provide FWHM, minimum/maximum
frequency and curve point count. Save CSV for plotting and JSON for units,
source sticks, warnings, status and provenance. Editing broadening changes the
display curve, not the source frequencies or intensities.

For QC output files, `openwfn FILE properties` extracts the reader's reported
energy, charge/spin and other available quantities. A successful extraction
does not reconstruct missing AO coefficients or make density analysis possible.

For API code that needs an error envelope instead of exceptions:

```python
from openwfn import load
from openwfn.analysis.registry import run_analysis_safe

calc = load("examples/research-workflows/biphenyl/biphenyl.molden")
result = run_analysis_safe(calc.data, "ir-spectrum")
if result.status == "failed":
    print(result.error.category, result.error.message)
```

The high-level `calc.analyze()` method retains its documented exception behavior.
Do not catch every failure and replace it with an empty successful result.

## Recheck numerical evidence

Run [the biphenyl comparisons](biphenyl/README.md),
[real-space comparisons](real-space/README.md) and
[printed spectroscopy comparisons](spectroscopy/README.md).
Hirshfeld's captured HORTON-PART references and grid-convergence procedure are
in `validation/hirshfeld/` and `scripts/validate_hirshfeld.py`; the external
reference tool is not a runtime requirement. Tests compare current native
charges against the captured external values for ten pinned molecules.

The interface-parity tests exercise Python, the assistant tool executor, MCP
and available direct CLI commands with the same inputs/settings. Matching
interfaces is not an independent numerical reference and does not test every
LLM/provider connection. The coverage runner retains unavailable/partial
outcomes; it is not a declaration that every property works for every molecule.
