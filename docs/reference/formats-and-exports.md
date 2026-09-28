# Formats, units, and exports

## Registered input suffixes

The parser registry accepts these filename suffixes. Files without a suffix may
still be recognized as single-frame XYZ when their contents match that format.

| Suffix | Parsed content |
|---|---|
| `.chk` | Gaussian binary checkpoint via the external `formchk` utility |
| `.cub` | Gaussian volumetric grid |
| `.cube` | Gaussian volumetric grid |
| `.fch` | Gaussian formatted checkpoint |
| `.fchk` | Gaussian formatted checkpoint and primary wavefunction path |
| `.log` | Gaussian calculation metadata |
| `.mol` | V2000 molecular structure |
| `.out` | Gaussian calculation metadata |
| `.pdb` | Molecular structure and available connectivity |
| `.sdf` | V2000 molecular structure |
| `.xyz` | Single-frame molecular structure |

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

The viewer and workbench embed [3Dmol.js](https://github.com/3dmol/3Dmol.js),
licensed under BSD-3-Clause, and retain that attribution in each generated file.
They do not load the rendering library from a remote server.

## Units

| Quantity | Presentation or control unit |
|---|---|
| Molecular coordinates and distances | ångström |
| Angles and dihedrals | degree |
| Orbital and total energies | atomic units unless labeled otherwise |
| Density-grid spacing and padding | bohr |
| Electrostatic potential | atomic units |

Always follow the label in machine-readable output and the installed version's help. See [scientific methods](../science/geometry-topology.md) for definitions.
