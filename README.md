<p align="center">
  <img src="docs/assets/images/openwfn-brand.svg" width="420" alt="openWFN">
</p>

<p align="center"><strong>Wavefunction analysis, made reproducible.</strong></p>

<p align="center">
  A unified post-processing toolkit for turning quantum-chemistry calculations into traceable, reproducible, review-ready results.
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

openWFN connects scientific analysis, automation, validation evidence, and research output through one typed calculation model. It works locally through the command line or Python, from individual calculations and high-throughput collections.

## Analyze · Automate · Validate · Publish

- **Analyze** molecular structure, orbitals, electron density, atomic populations, electrostatic potential, and derived properties.
- **Automate** with stable CLI commands, a typed Python API, structured results, resumable batches, and JSON/CSV exports.
- **Validate** using explicit capability status, parser provenance, transformations, numerical controls, and fixture-backed evidence.
- **Publish** durable reports, figures, cube files, structures, and batch manifests.

## Install

openWFN supports Python 3.10–3.13.

```bash
python -m pip install openwfn
openwfn --version
```

## First analysis

```bash
openwfn molecule.fchk doctor
openwfn molecule.fchk summary
openwfn molecule.fchk orbitals frontier
openwfn molecule.fchk population mulliken
openwfn molecule.fchk report build report.html
```

Run a collection of calculations with resumable, structured output:

```bash
openwfn batch ./calculations \
  --analysis summary \
  --analysis frontier \
  --output-dir ./results \
  --resume
```

Use JSON when another program will consume the result:

```bash
openwfn --format json --output summary.json molecule.fchk summary
```

## Capability map

| Area | Current capability | Status |
|---|---|---|
| Parsing and structure | FCHK records, molecular state, geometry, topology | Stable |
| Orbitals | Alpha/beta frontier energies and HOMO–LUMO gap | Stable |
| Population | Mulliken and symmetric Löwdin populations and charges | Stable |
| Density | Total, alpha, beta, and spin integration and cube export | Validated for active fixtures |
| Electrostatic potential | Nuclear and charge-model point ESP | Stable |
| Grid electronic/total ESP | Numerical Coulomb evaluation | Experimental |
| Automation | Versioned results, batch manifests, discovery, resume, JSON and CSV | Stable |
| Research reports | HTML/Markdown reports, tables, figures, and structures | Stable |
| Interactive workbench | Optional visualization and teaching surface | Experimental |

“Validated” is deliberately scoped. Review the [validation evidence](https://sha786muhammed.github.io/openWFN/science/validation-status/) and [limitations](https://sha786muhammed.github.io/openWFN/limitations/) before research use.

## Input support

Gaussian formatted-checkpoint (`.fchk`) data currently provides the full electronic wavefunction record used by openWFN analyses. Gaussian `.chk` is a proprietary binary format; openWFN calls Gaussian's separately installed `formchk` utility and does not decode it directly.

XYZ, MOL/SDF, and PDB inputs provide structure-only records. Additional quantum-chemistry parsers will be listed as supported only after their implementation and validation evidence are available.

```bash
openwfn calculation.chk formchk calculation.fchk
openwfn calculation.fchk convert --to sdf --output molecule.sdf
openwfn calculation.fchk density cube density.cube
```

## Documentation

- [First analysis](https://sha786muhammed.github.io/openWFN/start/first-analysis/)
- [CLI workflows](https://sha786muhammed.github.io/openWFN/guides/cli-workflows/)
- [Complete CLI reference](https://sha786muhammed.github.io/openWFN/reference/cli/)
- [Python API](https://sha786muhammed.github.io/openWFN/reference/python-api/)
- [Scientific methods](https://sha786muhammed.github.io/openWFN/science/geometry-topology/)
- [Validation status](https://sha786muhammed.github.io/openWFN/science/validation-status/)
- [Optional workbench](https://sha786muhammed.github.io/openWFN/workbench/)
- [Troubleshooting](https://sha786muhammed.github.io/openWFN/guides/troubleshooting/)

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
