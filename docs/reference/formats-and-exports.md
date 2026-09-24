# Formats, units, and exports

## Inputs

| Format | Support | Notes |
|---|---|---|
| Gaussian `.fchk` | Direct | Primary analysis format |
| Gaussian `.chk` | Via `formchk` | Requires licensed Gaussian utility in `PATH` |
| Gaussian `.cube` | Volumetric grid | `doctor` reports grid capability; molecular analyses require FCHK data |
| Gaussian `.log`/`.out` | Calculation metadata | `doctor` reports metadata capability; molecular analyses require FCHK data |
| XYZ, PDB, MOL/SDF | Molecular structure | Coordinates and available connectivity only |

`doctor` is safe to run across these input kinds. Other analysis commands fail
cleanly when the parsed input does not provide a molecular calculation; openWFN
does not infer missing wavefunction records.

## Structure outputs

`convert` writes XYZ, PDB, MOL, or SDF. These formats primarily carry structure and connectivity; they do not preserve the full wavefunction. The legacy `xyz` command writes atom symbols and Cartesian coordinates.

```bash
openwfn molecule.fchk convert --to sdf --output molecule.sdf
openwfn molecule.fchk xyz molecule.xyz
```

## Scientific outputs

Table and record output can be rendered as terminal tables, plain text, JSON, or CSV. JSON uses the versioned result envelope, including analysis identity, provenance, validation, warnings, timing, and structured failure fields. `export` writes frontier or population tables based on the destination extension. `plot frontier` writes a publication-oriented figure. `density cube` writes Gaussian cube volumetric data.

Batch runs write detailed JSON result records plus `batch-summary.csv`, a compact
index suitable for spreadsheets and dataframe ingestion.

## HTML outputs

`report build`, `workbench`, and `view` can create self-contained HTML. Reports are
supported research records when preserved with their machine-readable results. The
workbench is an optional Experimental visualization surface, not a numerical reference.
“Self-contained” means no openWFN server is required; it does not mean the artifact is
free of research data.

## Units

| Quantity | Presentation or control unit |
|---|---|
| Molecular coordinates and distances | ångström |
| Angles and dihedrals | degree |
| Orbital and total energies | atomic units unless labeled otherwise |
| Density-grid spacing and padding | bohr |
| Electrostatic potential | atomic units |

Always follow the label in machine-readable output and the installed version's help. See [scientific methods](../science/geometry-topology.md) for definitions.
