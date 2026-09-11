# openWFN

[![PyPI version](https://img.shields.io/pypi/v/openwfn)](https://pypi.org/project/openwfn/)
[![Python versions](https://img.shields.io/pypi/pyversions/openwfn)](https://pypi.org/project/openwfn/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://github.com/sha786muhammed/openWFN/actions/workflows/tests.yml/badge.svg)](https://github.com/sha786muhammed/openWFN/actions/workflows/tests.yml)

```text
██████╗ ██████╗ ███████╗███╗   ██╗██╗    ██╗███████╗███╗   ██╗
██╔══██╗██╔══██╗██╔════╝████╗  ██║██║    ██║██╔════╝████╗  ██║
██║  ██║██████╔╝█████╗  ██╔██╗ ██║██║ █╗ ██║█████╗  ██╔██╗ ██║
██║  ██║██╔═══╝ ██╔══╝  ██║╚██╗██║██║███╗██║██╔══╝  ██║╚██╗██║
██████╔╝██║     ███████╗██║ ╚████║╚███╔███╔╝██║     ██║ ╚████║
╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝ ╚══╝╚══╝ ╚═╝     ╚═╝  ╚═══╝
```

**openWFN 0.7** is a reproducible command-line and Python workbench for Gaussian
formatted-checkpoint analysis. It combines molecular geometry, orbitals, electron
density, population analysis, electrostatic potential, reports, and a portable
offline 3D workbench behind one typed calculation model.

[Read the complete documentation](https://sha786muhammed.github.io/openWFN/)

## Installation

```bash
pip install openwfn
```

## Quick Start

Run openWFN on a Gaussian formatted checkpoint file:

```bash
openwfn molecule.fchk summary
openwfn molecule.fchk geometry distance 1 2
openwfn molecule.fchk orbitals frontier
openwfn molecule.fchk population mulliken
openwfn molecule.fchk density integrate
openwfn molecule.fchk workbench molecule-workbench.html
```

If no subcommand is given:
- in a TTY terminal, `openwfn` launches interactive mode
- in non-interactive use, `openwfn` runs `summary`

## Supported Input

openWFN accepts both Gaussian `.fchk` and `.chk` files.

- `.fchk` files are read directly
- Gaussian `.chk` files are proprietary binary files. openWFN does not decode
  them directly; it calls Gaussian's `formchk` utility when that executable is
  available in your `PATH`. Users without Gaussian should supply a formatted
  `.fchk` file.

You can also run checkpoint conversion explicitly:

```bash
openwfn molecule.chk formchk
openwfn molecule.chk formchk molecule.fchk
```

## Analysis commands

- `summary` — molecular system summary
- `info` — formatted checkpoint metadata
- `geometry distance|angle|dihedral` — typed geometry analysis
- `bonds` — detected covalent bond network
- `graph` — fragment and connectivity graph
- `orbitals frontier` — HOMO, LUMO, and energy gap
- `population mulliken|lowdin` — atomic populations and charges
- `density integrate|cube` — numerical density integration and cube export
- `esp point` — nuclear, atomic-charge, or grid-based potential at a point
- `report build` — reproducible HTML or Markdown research report
- `workbench` — self-contained offline analysis and visualization workspace
- `xyz output.xyz` — export Cartesian coordinates
- `view` — export a standalone local HTML molecule viewer
- `formchk [output.fchk]` — convert a Gaussian checkpoint into a formatted checkpoint

## Viewer

`view` exports a fully local standalone HTML viewer powered by bundled `3Dmol.js`.

By default it:
- writes a shareable `.html` file in the current working directory
- keeps the viewer self-contained in a single file
- does not open the browser unless you request it

The exported viewer supports:
- atom labels
- local 3D rendering styles
- built-in downloads for `XYZ`, `PDB`, `SDF`, `PNG`, `JPEG`, and `SVG`

Examples:

```bash
openwfn molecule.fchk view
openwfn molecule.fchk view --open
openwfn molecule.fchk view --save viewer.html
```

## Example Sessions

```bash
openwfn examples/water/water.fchk summary
openwfn examples/water/water.fchk dist 2 1
openwfn examples/water/water.fchk angle 2 1 3
openwfn examples/methane/methane.fchk graph
openwfn examples/water/water.fchk view --save water_viewer.html
openwfn examples/water/water.fchk
```

## Capability status

openWFN labels scientific capabilities explicitly:

- **Stable:** parsing, geometry, topology, frontier orbitals, population analysis,
  nuclear/atomic-charge ESP, reports, exports, and the Python API.
- **Validated:** total-density grid integration and cube export for the active
  provenance-backed validation set.
- **Experimental:** electronic and total ESP obtained from numerical density grids.
- **Unsupported:** analyses whose required records or scientific validation are absent.

See the [validation matrix](https://sha786muhammed.github.io/openWFN/validation/)
and [documented limitations](https://sha786muhammed.github.io/openWFN/limitations/)
before using results in research.

## License

MIT License. See [LICENSE](LICENSE).
