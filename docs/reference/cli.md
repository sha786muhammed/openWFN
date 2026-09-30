# Command-line reference

```text
openwfn [GLOBAL OPTIONS] FILE COMMAND [COMMAND OPTIONS]
openwfn examples install DESTINATION [--overwrite]
```

Run `openwfn --help` or `openwfn FILE COMMAND --help` for the installed release's authoritative syntax.

For interoperable inputs in this development branch, install
`openwfn[interop]`, then inspect capabilities before an analysis:

```bash
openwfn molecule.molden capabilities
openwfn molecule.wfx orbitals frontier
openwfn calculation.out summary
openwfn batch ./calculations --analyses summary,frontier --output-dir ./results
```

Some output files contain geometry and energy but no complete wavefunction.
`capabilities` shows which analyses have their required fields; a Stable
format-ingestion status alone does not guarantee a `frontier` result.

## Global options

| Option | Purpose |
|---|---|
| `--version` | Print the installed version without requiring a file |
| `--format table\|plain\|json\|csv` | Select result rendering |
| `--input-format FORMAT_ID` | Select a registered parser for one ambiguous input or a homogeneous batch; place before `FILE` or `batch` |
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
| `capabilities` | Report normalized component and analysis availability |

## Inspection and structure

| Command | Syntax | Result |
|---|---|---|
| `summary` | `openwfn FILE summary` | Full calculation summary when data permit; otherwise a partial structure summary with unknown fields explicit |
| `info` | `openwfn FILE info` | Parsed FCHK scalar metadata |
| `doctor` | `openwfn FILE doctor` | Input kind, legacy availability fields, and normalized capability/analysis report |
| `capabilities` | `openwfn FILE capabilities` | Component states, parser/backend provenance, and registered-analysis requirements |
| `bonds` | `openwfn FILE bonds` | Covalent-radius bond heuristic |
| `graph` | `openwfn FILE graph` | Connected molecular fragments |
| `geometry` | `geometry distance I J` | Interatomic distance in ångströms |
| `geometry` | `geometry angle I J K` | Three-atom angle in degrees |
| `geometry` | `geometry dihedral I J K L` | Signed four-atom dihedral in degrees |

CLI atom indices are one-based. The legacy `dist`, `angle`, and `dihedral` forms remain accepted for existing scripts. Summary bond and fragment counts use a covalent-radius heuristic rather than authoritative FCHK connectivity; ghost centers are excluded from those physical structural summaries.

## Electronic analyses

| Command | Syntax and options | Status note |
|---|---|---|
| `orbitals` | `orbitals frontier [--spin alpha\|beta\|all]` | Requires MO energies; `all` reports both unrestricted channels and the true overall HOMO |
| `population` | `population mulliken` or `population lowdin` | Requires AO density and overlap data; conservation failures return `partial` with warnings |
| `density` | `density integrate [--kind total\|alpha\|beta\|spin] [--spacing BOHR] [--padding BOHR]` | Grid integration; validation status comes from the generated grid's conservation check |
| `density` | `density cube OUTPUT [grid options]` | Cube is written when requested; failed conservation returns `partial`/Experimental rather than a false Validated result |
| `cube` | `cube OUTPUT [grid options]` | Convenience density-cube command with the same validation behavior |
| `esp` | `esp point X Y Z [--component COMPONENT]` | Nuclear and charge-model components Stable; grid electronic/total Experimental |
| `validate` | `openwfn FILE validate` | Runs default total-density conservation check |

The accepted frontier selector is `--spin alpha|beta|all`. For an unrestricted calculation, use:

```bash
openwfn FILE orbitals frontier --spin all
```

The alpha-only default remains for backward compatibility and warns when a beta channel is also present. ECP and ghost-center electrostatics use effective nuclear charges from the FCHK source record when available.

Post-HF calculations do not silently imply use of a correlated density. When the parsed matrix is the SCF density, population and density results name that SCF density source and emit a warning. openWFN does not claim post-SCF density support unless such a density is explicitly parsed and selected.

The default density spacing is **0.15 bohr** with 6.0 bohr padding. This is an accuracy/performance starting point, not a universal convergence setting; check the result status and converge the grid for quantitative work.

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
`--analyses`, `--workers`, required `--output-dir`, and optional `--fail-fast`,
`--resume`, `--format-map MAP.json`, and `--spin alpha|beta|all` controls. The spin selector applies to a requested `frontier` analysis; for example:

```bash
openwfn batch ./calculations \
  --analyses frontier \
  --spin all \
  --output-dir ./results
```

This maps the requested frontier analysis to the spin-complete `frontier-all` result. Resume fingerprints include the frontier spin choice, so changing spin selection does not reuse incompatible cached results.

Batch records preserve scientifically usable `partial` analyses. A record is `error` only when every requested analysis fails; otherwise partial values, warnings, and result data are retained in the manifest.

The top-level batch result is `success`/exit 0 only when every input succeeds,
`partial`/exit 0 when at least one record is partial and none fail, and
`failed`/nonzero when an input errors or discovery finds an unsupported file.
An all-unsupported directory still writes a manifest. Its `unsupported_details`
list includes paths, reasons, and checksums when readable; `attempted_count`
and `stopped_early` describe fail-fast runs. A JSON format map resolves keys
relative to the map file, and unknown or conflicting format hints fail before
analysis records are written.

Resume requires matching input checksums and configuration fingerprints, including software, backend, analysis versions, and effective format hints; failed inputs are retried. Inputs may be files or directories. `--recursive` scans subdirectories and `--dry-run` previews supported and unsupported files without requiring `--output-dir`. Completed runs write `batch-manifest.json`, per-input JSON records, and `batch-summary.csv`. Progress uses stderr and global `--quiet` suppresses it, but `--quiet --format json` still emits the final result.
It writes result schema `1.0` envelopes inside batch manifest schema `1.0`.
The older `--operation summary` form remains supported.

With `--format json`, parsed commands emit one result envelope on stdout.
Runtime/input failures have `status="failed"`, structured error details, and
a nonzero exit code. `--output PATH` also saves that envelope to the requested
file. Help and argument-syntax errors remain ordinary text.

With multiple workers, openWFN keeps a bounded queue proportional to the worker
count. Per-input records are saved as workers finish, while the final manifest
and CSV index remain in deterministic input order.

`interactive` launches the guided terminal menu. With a file but no command, a
terminal session enters guided mode; redirected input or `--non-interactive`
defaults to `summary`.

The hidden `mo` developer preview is intentionally not part of the public command contract.
