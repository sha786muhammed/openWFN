# openWFN

![Tests](https://github.com/sha786muhammed/openWFN/actions/workflows/tests.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.10+-blue)

openWFN (open WaveFunction Network) is a lightweight toolkit for molecular geometry post-processing from Gaussian checkpoint data.

It is built for users who want:
- fast command-line geometry analysis from `.fchk` files
- reproducible atom-index-based calculations
- a minimal, script-friendly toolchain with low dependencies

## Key Capabilities
- Read Gaussian `.fchk` files
- Convert `.chk` to `.fchk` automatically when `formchk` is available
- Convert coordinate units from Bohr to Angstrom internally
- Calculate distance, angle, and dihedral from atom indices
- Detect covalent bonds using tabulated covalent radii
- Build molecular fragments (connected components)
- Export coordinates to XYZ format
- Run in command mode or interactive terminal menu mode

## Requirements
- Python 3.10+
- `numpy`
- Gaussian `formchk` only if you provide `.chk` files

## Installation
```bash
git clone https://github.com/sha786muhammed/openWFN.git
cd openWFN
pip install -e .
```

## Quick Start
Use one of the included examples:
```bash
openwfn examples/water/water.fchk summary
openwfn examples/ammonia/ammonia.fchk dist 1 2
openwfn examples/methane/methane.fchk graph
openwfn examples/water/water.fchk xyz water.xyz
```

If no subcommand is provided:
- in a TTY terminal, openWFN starts interactive mode
- in non-interactive contexts, openWFN runs `summary`

## Command Reference
General form:
```bash
openwfn <file.chk|file.fchk> <command> [arguments]
```

Available commands:
- `summary`: one-page molecular overview (formula, atom count, charge, multiplicity, center of mass, energy if present, bonds, fragments)
- `info`: print parsed scalar metadata from FCHK
- `dist i j`: distance in Angstrom between atom `i` and atom `j`
- `angle i j k`: bond angle (i-j-k) in degrees
- `dihedral i j k l`: torsion angle (i-j-k-l) in degrees
- `bonds`: print detected covalent bonds and distances
- `graph`: print molecular fragments (connected components)
- `xyz output.xyz`: export Cartesian coordinates to XYZ file
- `interactive`: force interactive menu mode
- `density --export out.vtk [--grid-size NxNxN]`: density export pathway (see status section)
- `mo <index> --export out.vtk`: molecular orbital pathway (see status section)

Get CLI help:
```bash
openwfn --help
```

## Interactive Mode Guide
Start:
```bash
openwfn examples/water/water.fchk
```

Main menu options:
```text
s. Molecular summary (Quick view)
1. Detailed metadata
2. Atom index table
3. Distance between two atoms
4. Bond angle (i-j-k)
5. Dihedral angle (i-j-k-l)
6. Export XYZ
7. Detect bonds / fragments
0. Exit
```

Typical interactive workflow:
1. Press `2` to print atom indices and coordinates.
2. Use those indices in `3`, `4`, or `5` for geometry calculations.
3. Press `7` to inspect fragments in multi-component systems.
4. Press `6` to export an XYZ file for external visualization.
5. Press `0` to exit.

Input behavior:
- atom indices are 1-based
- invalid indices are reported as errors
- malformed numeric input is rejected and reprompted

## Example Sessions
Distance and angle:
```bash
openwfn examples/water/water.fchk dist 2 1
openwfn examples/water/water.fchk angle 2 1 3
```

Molecular summary:
```bash
openwfn examples/ammonia/ammonia.fchk summary
```

Fragment detection:
```bash
openwfn examples/methane/methane.fchk graph
```

XYZ export:
```bash
openwfn examples/water/water.fchk xyz outputs/water.xyz
```

## File and Data Notes
- Atomic coordinates in Gaussian FCHK are read in Bohr and converted to Angstrom.
- Geometry commands assume coordinates are present in `Current cartesian coordinates`.
- Bond detection uses element covalent radii with a fixed scaling factor (currently `1.2` in code).

## Current Implementation Status
Fully supported and tested:
- parsing of essential scalar and coordinate data
- geometry calculations (`dist`, `angle`, `dihedral`)
- bond detection and graph fragments
- XYZ export

Partially implemented:
- `density` command interface exists, but electron-density evaluation backend is not fully implemented yet.
- `mo` command interface exists, but molecular-orbital grid evaluation is currently a stub.

Use these two commands only if you are extending the codebase.

## Development
Run tests:
```bash
pytest -q
```

Project layout:
```text
src/openwfn/        core library and CLI
tests/              unit tests
examples/           sample molecules and input files
```

## License
MIT License. See [LICENSE](LICENSE).

## Author
Muhammed Shah Shaji  
PhD Researcher, Computational Chemistry  
GitHub: https://github.com/sha786muhammed
