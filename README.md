<p align="center">
  <img src="docs/assets/images/openwfn-orbital-hero.webp" width="300" alt="openWFN molecular orbital visualization">
</p>

<p align="center">
  <img src="docs/assets/images/openwfn-wordmark.png" width="420" alt="openWFN — Wavefunction Analysis">
</p>

<p align="center"><strong>Wavefunction analysis for reproducible molecular insight</strong></p>

<p align="center">
  A local Python, command-line, reporting, and offline 3D workbench for Gaussian formatted-checkpoint data.
</p>

<p align="center">
  <a href="https://pypi.org/project/openwfn/"><img alt="PyPI" src="https://img.shields.io/pypi/v/openwfn?label=PyPI&color=4051b5"></a>
  <a href="https://pypi.org/project/openwfn/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/openwfn?color=00a6c7"></a>
  <a href="https://github.com/sha786muhammed/openWFN/actions/workflows/tests.yml"><img alt="Tests" src="https://github.com/sha786muhammed/openWFN/actions/workflows/tests.yml/badge.svg"></a>
  <a href="https://sha786muhammed.github.io/openWFN/"><img alt="Documentation" src="https://github.com/sha786muhammed/openWFN/actions/workflows/docs.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-4051b5"></a>
</p>

<p align="center">
  <a href="https://sha786muhammed.github.io/openWFN/start/first-analysis/"><strong>Get started</strong></a>
  · <a href="https://sha786muhammed.github.io/openWFN/reference/cli/">CLI reference</a>
  · <a href="https://sha786muhammed.github.io/openWFN/science/validation-status/">Validation</a>
  · <a href="https://sha786muhammed.github.io/openWFN/citation/">Citation</a>
</p>

---

openWFN connects molecular geometry, topology, orbitals, electron density, population analysis, electrostatic potential, reproducible reports, and portable offline visualization through one typed calculation model. It is designed for researchers who need results that can be inspected, exported, and checked—not only displayed.

## Why openWFN

- **Inspect** molecular state, FCHK metadata, geometry, bonds, and fragments.
- **Analyze** frontier orbitals, density, Mulliken and Löwdin populations, and ESP.
- **Automate** with structured JSON/CSV output, a Python API, and batch manifests.
- **Communicate** through self-contained reports, figures, cube files, and an offline workbench.
- **Evaluate trust** with explicit Stable, Validated, Experimental, and Unsupported labels.
- **Keep data local**: core analysis does not require an openWFN account or upload service.

## Install

openWFN supports Python 3.10–3.13.

```bash
python -m pip install openwfn
openwfn --version
```

## First analysis

```bash
openwfn molecule.fchk summary
openwfn molecule.fchk doctor
openwfn molecule.fchk geometry distance 1 2
openwfn molecule.fchk geometry angle 2 1 3
openwfn molecule.fchk orbitals frontier
openwfn molecule.fchk population mulliken
```

Generate a portable local workbench:

```bash
openwfn molecule.fchk workbench molecule-workbench.html --open
```

Or request machine-readable output:

```bash
openwfn --format json --output summary.json molecule.fchk summary
```

## Capability map

| Area | What v0.7 provides | Status |
|---|---|---|
| Parsing and structure | FCHK records, molecular state, geometry, topology | Stable |
| Orbitals | alpha/beta frontier energies and HOMO–LUMO gap | Stable |
| Population | Mulliken and symmetric Löwdin populations/charges | Stable |
| Density | total/alpha/beta/spin integration and cube export | Validated for active fixtures |
| Electrostatic potential | nuclear and charge-model point ESP | Stable |
| Grid electronic/total ESP | numerical Coulomb evaluation | Experimental |
| Research output | HTML/Markdown reports, tables, figures, batch manifests | Stable |
| Visualization | standalone viewer and offline workbench | Stable |

“Validated” is deliberately scoped: current provenance-backed cases are water, methane, and ammonia. Read the [validation evidence](https://sha786muhammed.github.io/openWFN/science/validation-status/) and [limitations](https://sha786muhammed.github.io/openWFN/limitations/) before research use.

## Input and output

`.fchk` is the primary input. Gaussian `.chk` files use a proprietary binary format; openWFN calls Gaussian's separately installed `formchk` utility and does not decode that binary format itself.

```bash
openwfn calculation.chk formchk calculation.fchk
openwfn calculation.fchk convert --to sdf --output molecule.sdf
openwfn calculation.fchk density cube density.cube
openwfn calculation.fchk report build report.html
```

Structure exports include XYZ, PDB, MOL, and SDF. Scientific records can be rendered as tables, plain text, JSON, or CSV.

## Documentation paths

- [Learn the concepts](https://sha786muhammed.github.io/openWFN/learn/wavefunction-analysis/)
- [Follow a CLI workflow](https://sha786muhammed.github.io/openWFN/guides/cli-workflows/)
- [Look up every public command](https://sha786muhammed.github.io/openWFN/reference/cli/)
- [Study equations and assumptions](https://sha786muhammed.github.io/openWFN/science/geometry-topology/)
- [Use the Python API](https://sha786muhammed.github.io/openWFN/reference/python-api/)
- [Troubleshoot an analysis](https://sha786muhammed.github.io/openWFN/guides/troubleshooting/)

## Security and privacy

Computations are local, but input and generated artifacts can contain unpublished research. Never post private checkpoint files, credentials, personal filesystem paths, or license details in public issues. Read the [security and data-privacy guide](https://sha786muhammed.github.io/openWFN/project/security/).

## Development

```bash
python -m pip install -e ".[test,docs]"
python -m pytest
python -m ruff check .
python scripts/run_validation.py
python scripts/check_docs.py --root .
python -m mkdocs build --strict
```

Contributions should include tests, documented units and assumptions, and validation evidence appropriate to the claim. See [Contributing](https://sha786muhammed.github.io/openWFN/project/contributing/).

## Citation and license

Cite the exact version used and the project repository; see the [citation guide](https://sha786muhammed.github.io/openWFN/citation/). openWFN is released under the [MIT License](LICENSE).

**Author:** Muhammed Shah Shaji, University of Louisville
