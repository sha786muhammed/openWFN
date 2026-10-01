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

`doctor` uses the canonical loader across these input kinds. `summary` returns
a partial structure record when geometry exists but a full wavefunction does
not. Electronic analyses fail cleanly when required records are absent.

## Stable interoperability formats

In 0.9.1, Molden detection also accepts `.molden.input` and recognizes
the `[Molden Format]` header for unrecognized filenames. Structure exports warn
when molecular charge or spin multiplicity cannot be retained, in addition to
ghost/ECP warnings. Keep the original calculation and its metadata; reloading a
structure export is not an electronic-state round-trip.

This section describes openWFN 0.9.1. Install
`python -m pip install "openwfn[interop]==0.9.1"` for the IOData-backed entries. This is the
pinned IOData 1.0.1 readable-format inventory. “Stable” means ingestion passed
the project fixture contract; it does not mean every analysis is available,
or that all real-world variants have been independently validated. Native
FCHK remains the preferred path for Gaussian formatted checkpoints. The
“components” column describes the pinned fixture, not a promise about every
file in that format. `calculation` can be structure-only and does not imply
that orbitals or a basis are present.

| Format ID | Typical filename | Preferred path | Fixture components | Ingestion status |
|---|---|---|---|---|
| `charmm` | `.crd`, `.psf` | IOData | metadata, structure | Stable |
| `chgcar` | `CHGCAR`, `CHGCAR-*`, `.chgcar` | IOData | grids, metadata, periodic, structure | Stable |
| `cp2klog` | CP2K `.out` | IOData; detected from content | calculation, metadata, structure | Stable |
| `cube` | `.cube`, `.cub` | Native | grids | Stable |
| `extxyz` | `.extxyz` | IOData | metadata, structure | Stable |
| `fchk` | `.fchk`, `.fch` | Native | calculation, metadata, structure | Stable |
| `fcidump` | `FCIDUMP`, `.fcidump` | IOData | integrals | Stable |
| `gamess` | GAMESS `.dat` or `.out` | IOData; explicit hint may be needed | metadata, structure | Stable |
| `gaussianinput` | `.gjf`, `.com` | IOData | metadata, structure | Stable |
| `gaussianlog` | Gaussian `.log` | Native by default; IOData with explicit hint | metadata | Stable |
| `gromacs` | `.gro` | IOData | metadata, periodic, structure | Stable |
| `json_qcschema` | `.qcschema.json` | IOData | metadata, structure | Stable |
| `locpot` | `LOCPOT`, `LOCPOT-*`, `.locpot` | IOData | grids, metadata, periodic, structure | Stable |
| `mol2` | `.mol2` | IOData | metadata, structure | Stable |
| `molden` | `.molden` | IOData | calculation, metadata, structure | Stable |
| `molekel` | `.mkl` | IOData | calculation, structure | Stable |
| `mwfn` | `.mwfn` | IOData | calculation, metadata, structure | Stable |
| `orcalog` | ORCA `.out` | IOData; detected from content | metadata, structure | Stable |
| `pdb` | `.pdb` | Native | calculation, metadata, structure | Stable |
| `poscar` | `POSCAR`, `POSCAR-*`, `.poscar`, `.vasp` | IOData | metadata, periodic, structure | Stable |
| `qchemlog` | Q-Chem `.out` | IOData; detected from content | metadata, structure | Stable |
| `sdf` | `.sdf`, `.mol` | Native | calculation, metadata, structure | Stable |
| `wfn` | `.wfn` | IOData | calculation, metadata, structure | Stable |
| `wfx` | `.wfx` | IOData | calculation, metadata, structure | Stable |
| `xyz` | `.xyz` | Native | calculation, metadata, structure | Stable |

The 25 fixture contracts and cross-format numerical checks are recorded in
[`validation/interop`](https://github.com/sha786muhammed/openWFN/tree/main/validation/interop).
The five water wavefunction representations share one originating calculation;
their agreement is a cross-format regression, not independent experimental
confirmation. WFN/WFX expose 21 primitive functions where the contracted
FCHK/Molden/MWFN representations expose 13 basis functions.

## Structure outputs

`convert` writes XYZ, PDB, MOL, or SDF. These formats primarily carry structure and connectivity; they do not preserve the full wavefunction. The legacy `xyz` command writes atom symbols and Cartesian coordinates.
When a source contains ghost or ECP effective nuclear charges, these outputs
warn that the charges cannot survive the conversion. The direct Python
`write_structure` function returns the same warning strings. Cube headers
retain effective nuclear charges.

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
