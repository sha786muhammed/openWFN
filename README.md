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

**openWFN** is a command-line toolkit for molecular geometry, connectivity, and structure exploration from Gaussian checkpoint data. It is designed for fast terminal workflows around formatted checkpoint files, with a built-in local molecule viewer for lightweight inspection and sharing.

## Installation

```bash
pip install openwfn
```

## Quick Start

Run openWFN on a Gaussian formatted checkpoint file:

```bash
openwfn molecule.fchk summary
openwfn molecule.fchk dist 1 2
openwfn molecule.fchk graph
openwfn molecule.fchk xyz molecule.xyz
openwfn molecule.fchk view
```

If no subcommand is given:
- in a TTY terminal, `openwfn` launches interactive mode
- in non-interactive use, `openwfn` runs `summary`

## Supported Input

openWFN accepts both Gaussian `.fchk` and `.chk` files.

- `.fchk` files are read directly
- `.chk` files are converted to `.fchk` automatically when Gaussian's `formchk` utility is available in your `PATH`

You can also run checkpoint conversion explicitly:

```bash
openwfn molecule.chk formchk
openwfn molecule.chk formchk molecule.fchk
```

## Stable Commands

- `summary` — molecular system summary
- `info` — formatted checkpoint metadata
- `dist i j` — interatomic distance
- `angle i j k` — three-atom bond angle
- `dihedral i j k l` — four-atom dihedral
- `bonds` — detected covalent bond network
- `graph` — fragment and connectivity graph
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

## Project Scope

The stable surface of openWFN is focused on:
- geometry analysis
- molecular connectivity and fragment inspection
- coordinate export
- local browser-based structure viewing

Experimental modules may exist in the codebase, but they are not presented as production-ready features.

## License

MIT License. See [LICENSE](LICENSE).
