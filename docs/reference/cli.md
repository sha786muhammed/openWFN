# Command-line reference

```text
openwfn [GLOBAL OPTIONS] FILE COMMAND [COMMAND OPTIONS]
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

## Inspection and structure

| Command | Syntax | Result |
|---|---|---|
| `summary` | `openwfn FILE summary` | Formula, state, energy, center of mass, bonds, fragments |
| `info` | `openwfn FILE info` | Parsed FCHK scalar metadata |
| `doctor` | `openwfn FILE doctor` | Availability of basis, orbitals, and density |
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
| `workbench` | `workbench [OUTPUT] [--open]` | Standalone offline HTML workbench |
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
It writes result schema `1.0` envelopes inside batch manifest schema `1.0`.
The older `--operation summary` form remains supported.

`interactive` launches the guided terminal menu. With no command, a terminal session enters guided mode; redirected/non-interactive use defaults to `summary`.

The hidden `mo` developer preview is intentionally not part of the public command contract.
