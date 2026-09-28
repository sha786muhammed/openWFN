# Command-line reference

```text
openwfn [GLOBAL OPTIONS] FILE COMMAND [COMMAND OPTIONS]
openwfn examples install DESTINATION [--overwrite]
```

Run `openwfn --help` or `openwfn FILE COMMAND --help` for the installed release's authoritative syntax.

## Global options

| Option | Purpose |
|---|---|
| `--version` | Print the installed version without requiring a file |
| `--format table\|plain\|json\|csv` | Select result rendering |
| `--output PATH` | Write supported rendered output to a file |
| `--quiet`, `--verbose`, `--debug` | Control diagnostic detail |
| `--no-color`, `--plain`, `--compact` | Control terminal presentation |
| `--overwrite` | Permit replacement of an existing output |
| `--non-interactive` | Disable interactive behavior |

## Installed examples

`openwfn examples install DIRECTORY` copies maintained, redistributable inputs
from the installed wheel. The command checks every destination before writing
and refuses to replace existing files. Pass `--overwrite` only when replacement
is intentional.

## Command families

These are the public top-level choices shown by `openwfn --help`.

| Command | Purpose |
|---|---|
| `examples` | Install packaged example inputs |
| `summary` | Summarize molecular identity and calculation state |
| `info` | Show detailed FCHK metadata |
| `dist` | Legacy distance command |
| `angle` | Legacy angle command |
| `dihedral` | Legacy dihedral command |
| `bonds` | Detect bonds with the covalent-radius heuristic |
| `xyz` | Legacy XYZ export |
| `formchk` | Invoke Gaussian's external checkpoint converter |
| `view` | Create a standalone local molecular viewer |
| `interactive` | Start the guided terminal interface |
| `graph` | Show molecular fragments |
| `geometry` | Run distance, angle, and dihedral operations |
| `population` | Run Mulliken or Löwdin population analysis |
| `orbitals` | Inspect frontier orbitals |
| `density` | Integrate or export electron and spin density |
| `esp` | Evaluate supported electrostatic-potential components |
| `report` | Build a research report |
| `workbench` | Build the optional Experimental workbench |
| `cube` | Export an electron-density cube |
| `convert` | Convert molecular structure formats |
| `export` | Export a registered result table |
| `plot` | Create a supported scientific figure |
| `batch` | Analyze multiple inputs |
| `validate` | Run the density-conservation check |
| `doctor` | Inspect input type and available capabilities |

## Inspection and structure

| Command | Syntax | Result |
|---|---|---|
| `summary` | `openwfn FILE summary` | Formula, state, energy, center of mass, bonds, fragments |
| `info` | `openwfn FILE info` | Parsed FCHK scalar metadata |
| `doctor` | `openwfn FILE doctor` | Input kind and availability of metadata, grid, basis, orbitals, and density |
| `bonds` | `openwfn FILE bonds` | Covalent-radius bond heuristic |
| `graph` | `openwfn FILE graph` | Connected molecular fragments |
| `geometry` | `geometry distance I J` | Interatomic distance in ångströms |
| `geometry` | `geometry angle I J K` | Three-atom angle in degrees |
| `geometry` | `geometry dihedral I J K L` | Signed four-atom dihedral in degrees |

CLI atom indices are one-based. The legacy `dist`, `angle`, and `dihedral` forms remain accepted for existing scripts.

## Electronic analyses

| Command | Syntax and options | Status note |
|---|---|---|
| `orbitals` | `orbitals frontier [--spin alpha\|beta]` | Requires MO energies; Stable |
| `population` | `population mulliken` or `population lowdin` | Requires AO density and overlap data; Stable |
| `density` | `density integrate [--kind total\|alpha\|beta\|spin] [--spacing BOHR] [--padding BOHR]` | Grid integration; Validated for the active set |
| `density` | `density cube OUTPUT [grid options]` | Gaussian cube export; Validated for the active set |
| `cube` | `cube OUTPUT [grid options]` | Convenience density-cube command |
| `esp` | `esp point X Y Z [--component COMPONENT]` | Nuclear and charge-model components Stable; grid electronic/total Experimental |
| `validate` | `openwfn FILE validate` | Runs default total-density conservation check |

ESP components are `nuclear`, `mulliken`, `lowdin`, `electronic`, and `total`. Coordinates are Cartesian; consult [methods and units](../science/population-esp.md).

## Reports, exports, and visualization

| Command | Syntax | Output |
|---|---|---|
| `report` | `report build OUTPUT [--report-format html\|markdown] [--analyses LIST]` | Self-contained research report |
| `workbench` | `workbench [OUTPUT] [--open]` | Optional Experimental offline visualization |
| `view` | `view [--save HTML] [--open] [--no-labels] [--style ballstick\|stick]` | Standalone molecular viewer |
| `xyz` | `xyz OUTPUT` | Legacy XYZ export |
| `convert` | `convert --to xyz\|pdb\|mol\|sdf --output PATH` | Structure conversion |
| `export` | `export frontier\|mulliken\|lowdin OUTPUT` | Result table selected by extension |
| `plot` | `plot frontier OUTPUT [--dpi N]` | Frontier-orbital figure |
| `formchk` | `formchk [OUTPUT]` | Calls Gaussian's external `formchk` utility |

## Batch and guided mode

`batch` accepts the primary file plus additional inputs, comma-separated
`--analyses`, `--workers`, required `--output-dir`, and optional `--fail-fast`
and `--resume` flags. Resume requires matching input checksums and configuration
fingerprints; failed inputs are retried.
Inputs may be files or directories. `--recursive` scans subdirectories and
`--dry-run` previews supported and unsupported files without requiring
`--output-dir`. Completed runs write `batch-manifest.json`, per-input JSON
records, and `batch-summary.csv`. Progress uses stderr and global `--quiet`
suppresses it.
It writes result schema `1.0` envelopes inside batch manifest schema `1.0`.
The older `--operation summary` form remains supported.

With multiple workers, openWFN keeps a bounded queue proportional to the worker
count. Per-input records are saved as workers finish, while the final manifest
and CSV index remain in deterministic input order.

`interactive` launches the guided terminal menu. With a file but no command, a
terminal session enters guided mode; redirected input or `--non-interactive`
defaults to `summary`.

The hidden `mo` developer preview is intentionally not part of the public command contract.
