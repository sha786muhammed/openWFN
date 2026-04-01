# openWFN

[![PyPI version](https://img.shields.io/pypi/v/openwfn)](https://pypi.org/project/openwfn/)
[![Python versions](https://img.shields.io/pypi/pyversions/openwfn)](https://pypi.org/project/openwfn/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://github.com/sha786muhammed/openWFN/actions/workflows/tests.yml/badge.svg)](https://github.com/sha786muhammed/openWFN/actions/workflows/tests.yml)

```text
  ___   ____   _____  _   _ __        __ _____  _   _
 / _ \ |  _ \ | ____|| \ | |\ \      / /|  ___|| \ | |
| | | || |_) ||  _|  |  \| | \ \ /\ / / | |_   |  \| |
| |_| ||  __/ | |___ | |\  |  \ V  V /  |  _|  | |\  |
 \___/ |_|    |_____||_| \_|   \_/\_/   |_|    |_| \_|
```

openWFN is a lightweight command-line toolkit for molecular geometry analysis from Gaussian checkpoint data. It is designed for fast, script-friendly workflows around `.fchk` files.

## Installation

```bash
pip install openwfn
```

## Start

Run openWFN on a formatted checkpoint file:

```bash
openwfn molecule.fchk summary
openwfn molecule.fchk dist 1 2
openwfn molecule.fchk graph
openwfn molecule.fchk xyz molecule.xyz
openwfn molecule.fchk view
openwfn molecule.fchk view --open
openwfn molecule.chk formchk
```

If no subcommand is provided:
- in a TTY terminal, `openwfn` starts interactive mode
- in non-interactive contexts, `openwfn` runs `summary`

Stable commands:
- `summary`
- `info`
- `dist i j`
- `angle i j k`
- `dihedral i j k l`
- `bonds`
- `graph`
- `xyz output.xyz`
- `view`
- `formchk [output.fchk]`

`openwfn` accepts both `.fchk` and `.chk` inputs. When a `.chk` file is provided for
analysis, openWFN will use Gaussian's `formchk` utility automatically if it is
available in your `PATH`. You can also run conversion explicitly:

```bash
openwfn molecule.chk formchk
openwfn molecule.chk formchk molecule.fchk
```

`view` exports a fully local standalone HTML molecule viewer powered by bundled
`3Dmol.js`. By default it writes a shareable `.html` file in the current working
directory and does not open a browser unless `--open` is requested. The exported
viewer supports atom labels, style toggles, and built-in downloads for `XYZ`,
`PDB`, `SDF`, `PNG`, `JPEG`, and `SVG`.

## Example Sessions

```bash
openwfn examples/water/water.fchk summary
openwfn examples/water/water.fchk dist 2 1
openwfn examples/water/water.fchk angle 2 1 3
openwfn examples/methane/methane.fchk graph
openwfn examples/water/water.fchk view
openwfn examples/water/water.fchk view --open
openwfn examples/water/water.fchk
```

To save a standalone viewer file:

```bash
openwfn examples/water/water.fchk view --save viewer.html
```

## Release

Build and validate:

```bash
python -m build --no-isolation
python -m twine check dist/*
```

Upload to PyPI:

```bash
python -m twine upload dist/*
```

## License

MIT License. See [LICENSE](LICENSE).
