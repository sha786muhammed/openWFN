# Formats, units, and exports

Find the formats openWFN can read and write, and the units used in results.
Run `openwfn FILE capabilities` to see what your particular file supports.

## Registered input suffixes

The parser registry accepts these filename suffixes. Files without a suffix may
still be recognized as single-frame XYZ when their contents match that format.

| Suffix | Parsed content |
|---|---|
| `.chk` | Gaussian binary checkpoint via the external `formchk` utility |
| `.cub` | Gaussian volumetric grid |
| `.cube` | Gaussian volumetric grid |
| `.fch` | Gaussian formatted checkpoint |
| `.fchk` | Gaussian formatted checkpoint with native wavefunction records |
| `.log` | Gaussian calculation metadata |
| `.mol` | V2000 molecular structure |
| `.out` | Gaussian calculation metadata |
| `.pdb` | Molecular structure and available connectivity |
| `.sdf` | V2000 molecular structure |
| `.xyz` | Single-frame molecular structure |

`doctor` uses the canonical loader across these input kinds. `summary` returns
a partial structure record when geometry exists but a full wavefunction does
not. Electronic analyses fail cleanly when required records are absent.
Element symbols can still provide a formula and atom count when effective
nuclear charges are missing. Explicit ghost centers are excluded. In that case,
the formula describes the reported element composition; physical-nucleus and
ghost/ECP classification remain unconfirmed and are not inferred from symbols.

## Stable interoperability formats

Molden detection accepts `.molden.input` and recognizes
the `[Molden Format]` header for unrecognized filenames. Structure exports warn
when molecular charge or spin multiplicity cannot be retained, in addition to
ghost/ECP warnings. Keep the original calculation and its metadata; reloading a
structure export is not an electronic-state round-trip.

openWFN includes the IOData reader in its base installation. This is the pinned IOData 1.0.1
readable-format inventory. “Stable” means ingestion passed
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
openwfn molecule.molden convert --to sdf --output molecule.sdf
openwfn molecule.molden xyz molecule.xyz
```

## Scientific outputs

Read results as terminal text, JSON or CSV. JSON keeps the complete result,
including units, source information, warnings and diagnostics. `export` saves
frontier-orbital or population tables. `plot frontier` makes a figure from the
result, and `density cube` saves a volumetric field in cube format.

Keep JSON beside CSV curves when you need complete units, settings, warnings and
source information. CSV is a tabular view, not the complete result record.
Frontier and general population table exports include result status, warnings
and provenance columns. A failed analysis can be saved as an error record in
JSON, but not as an empty scientific CSV table. Table and spectrum exports are
published only after writing finishes; a failed write leaves an existing output
unchanged. HTML reports embed complete result records, including failed analyses.

Batch runs write detailed JSON result records plus `batch-summary.csv`, a compact
index suitable for spreadsheets and dataframe ingestion.

## HTML outputs

`report build`, `workbench`, and `view` can create self-contained HTML. Reports are
supported research records when preserved with their machine-readable results. The
workbench is an optional visualization surface with a Stable interface for the tested Chromium scope, not a numerical reference.
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
| Wavefunction orbital and total energies | hartree; gaps also reported in eV |
| Source-output frontier energies and excitation energies | eV |
| Density-grid spacing and padding | bohr |
| CLI/high-level API ESP point coordinates | ångström |
| Electrostatic potential | hartree/e |
| Density-derivative, ELF/LOL/NCI and QTAIM coordinates | bohr |

Always follow the label in machine-readable output and the installed version's help. See [scientific methods](../science/geometry-topology.md) for definitions.
