# Python workflows

Use Python to analyse files in a notebook or script. Load your file, check
which analyses are available, then read the result and its warnings.

```python
from openwfn import load

calculation = load("molecule.molden")
print(len(calculation.molecule.atoms))
print(calculation.molecule.charge)
print(calculation.molecule.metadata.energy_hartree)
```

`OpenWFNCalculation` gives access to the structure and available electronic
data. Missing basis, orbital or density records remain missing.

For reproducible automation, prefer the registered interface:

```python
result = calculation.analyze("frontier")
print(result.data["gap_ev"], result.units["gap_ev"])
print(result.provenance["input_sha256"])
```

`analyze(name)` records the analysis identity, version, elapsed time, source
warnings, and input provenance. The specialized methods below are convenient
when their explicit parameters make a script clearer. They also return
`ResultRecord` objects and retain input provenance.

## Geometry

```python
oh = calculation.geometry_distance(1, 2)
hoh = calculation.geometry_angle(2, 1, 3)
print(oh.data["value"])
print(hoh.data["value"])
```

The high-level geometry methods and the public `distance`, `angle`, `dihedral`,
`detect_bonds`, and graph helpers use one-based atom numbers, matching the CLI.
Internal sequences such as `molecule.atoms`, orbital coefficient arrays,
`BasisShell.atom_index`, and `Bond.atom1`/`Bond.atom2` use zero-based Python
indices. Do not pass those internal indices directly to geometry methods without
adding one.

`analyze_geometry()` returns a `ResultRecord`; read its values from `.data`.

## Batch analyses

```python
from pathlib import Path

from openwfn import run_batch

manifest = run_batch(
    inputs=[Path("calculations")],
    operation=None,
    analyses=("summary", "frontier"),
    workers=2,
    output_dir=Path("batch-results"),
    resume=True,
    recursive=True,
)
print(manifest.schema_version, manifest.analyses)
```

The manifest preserves input order and records successful, partial, skipped,
and failed inputs without discarding completed analyses. Resume reuses only
records with matching input checksums and configuration fingerprints.
The output directory also contains `batch-summary.csv` for spreadsheet and
dataframe workflows. Use `discover_inputs(...)` directly when an application
needs to preview supported and unsupported paths before execution.

## Density and orbitals

```python
frontier = calculation.orbitals("alpha")
population = calculation.population("mulliken")
integral = calculation.density("total", spacing_bohr=0.20, padding_bohr=6.0)
```

`orbitals()` accepts `"alpha"`, `"beta"` or `"all"`. `population()` accepts
`"mulliken"`, `"lowdin"` or `"hirshfeld"`. `density()` accepts `"total"`, `"alpha"`,
`"beta"`, or `"spin"`; it integrates that density on a generated grid rather
than returning the grid itself. Invalid option values raise `ValueError`.
High-level analyses report missing records as failed `ResultRecord` objects;
check `.status` and `.error` before using `.data`. Low-level evaluators may
raise `DataUnavailableError` directly.

The public package exports low-level evaluators including `compute_density`, `evaluate_mo`, and `make_bounding_box_grid`. These require compatible basis, coefficient, and density data. Prefer the typed model as the source and validate numerical settings before treating a grid result as converged.

For the complete export list and signatures, see [Python API reference](../reference/python-api.md). For runnable command-line equivalents, see [CLI workflows](cli-workflows.md).
