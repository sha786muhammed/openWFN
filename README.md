<p align="center">
  <img src="docs/assets/images/openwfn-brand.svg" width="420" alt="openWFN">
</p>

<p align="center"><strong>Wavefunction analysis, made reproducible.</strong></p>

<p align="center">
  A unified post-processing toolkit for turning quantum-chemistry calculations into traceable, reproducible, review-ready results.
</p>

<p align="center">
  <a href="https://pypi.org/project/openwfn/"><img alt="PyPI" src="https://img.shields.io/pypi/v/openwfn?label=PyPI&color=4051b5&cacheSeconds=300"></a>
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

## Staged QC development branch

The development branch includes [11 real molecular examples](examples/everyday-qc/README.md)
and a [complete Experimental coverage audit](docs/project/experimental-coverage.md).
The audit retains ESP convergence failures and unsupported legacy entry points.

The stable release remains **0.9.2**. The `feat/everyday-qc-staged` branch adds
these **Validated** methods within the documented reference scope; they are not yet part of a published release.

| Development capability | Scientific controls |
|---|---|
| Signed MO cubes, arbitrary MO/HOMO/LUMO, alpha/beta | AO/grid norm diagnostics, bounded chunks, input-hash cube comments |
| Mulliken/Löwdin MO composition | Named convention, atom/shell/angular partitions, raw norm and overlap conditioning |
| Spin-corrected Mayer bond orders | Total/spin conservation, density provenance, full matrix and filtered pairs |
| Orbital-energy DOS/PDOS | Gaussian sigma/range controls, spin channels, projection sum rules, CSV/JSON/PNG/SVG |

See the [design and roadmap](docs/project/everyday-qc-design.md),
[validation and limitations](docs/project/everyday-qc-validation.md), and
[method documentation](docs/science/dos-pdos.md). Native Hirshfeld and later
spectroscopy/real-space phases are not implemented; the validation document
records their scientific gates. Existing CLI/API/result schemas are retained.

## Install

openWFN supports Python 3.10–3.13.

Install the stable release:

```bash
python -m pip install --upgrade openwfn
openwfn --version
```

Install the exact release when reproducing research:

```bash
python -m pip install openwfn==0.9.2
```

## First analysis

```bash
openwfn examples install ./openwfn-examples
openwfn ./openwfn-examples/water.fchk doctor
openwfn ./openwfn-examples/water.fchk summary
openwfn ./openwfn-examples/water.fchk orbitals frontier
```

For your own calculation, replace the example path:

```bash
openwfn molecule.fchk summary
```

Run a collection of calculations with resumable, structured output:

```bash
openwfn batch ./calculations \
  --analyses summary,frontier \
  --output-dir ./results \
  --resume
```

Use JSON when another program will consume the result:

```bash
openwfn --format json --output summary.json molecule.fchk summary
```

## Scientific correctness safeguards

openWFN uses source-faithful electronic metadata wherever Gaussian FCHK provides it. ECP and ghost centers use the file's effective nuclear charges instead of blindly substituting atomic numbers, and density validation prefers the source electron-count records. Population and density conservation failures return partial results with warnings rather than presenting inconsistent numbers as clean successes.

For unrestricted calculations, request the spin-complete frontier view with `openwfn FILE orbitals frontier --spin all`; batch workflows support the same spin selection. Post-HF files explicitly report when the available SCF density is being analyzed rather than implying that a correlated density was used.

The default density spacing of **0.15 bohr** is an accuracy/performance tradeoff, not a universal convergence guarantee. Check the returned conservation status and converge spacing/padding for the system and property being reported.

## Capability map

| Area | Current capability | Status |
|---|---|---|
| Parsing and structure | FCHK records, molecular state, geometry, topology | Stable |
| Orbitals | Alpha/beta and spin-complete frontier energies and HOMO–LUMO information | Stable interface; fixture-backed regressions |
| Population | Mulliken and symmetric Löwdin populations and charges | Stable interface; conservation checked and fixture-scoped |
| Density | Total, alpha, beta, and spin integration and cube export | Validated only for the named active validation fixtures and tolerances |
| Electrostatic potential | Nuclear and charge-model point ESP | Stable interface; special-case regressions included |
| Gaussian-integral electronic/total ESP | AO-density Coulomb integrals with independent references | Validated for the eleven-case set |
| Grid electronic/total ESP | Numerical Coulomb evaluation | Experimental |
| Automation | Versioned results, batch manifests, discovery, resume, JSON and CSV | Stable |
| Research reports | HTML/Markdown reports, tables, figures, and structures | Stable |
| Interactive workbench | Offline workspaces, surfaces and signed geometry readouts | Stable interface; eleven-molecule Chromium evidence; field diagnostics retained |
| Additional input formats | Optional IOData ingestion and file-specific capabilities | Stable fixture contract; requires the interop extra |
| QC output properties | Source-reported extraction with optional cclib | Experimental; not a complete wavefunction |
| Local MCP | Read-only stdio tools for selected analyses | Experimental; no remote service |

“Validated” is deliberately scoped. Review the [validation evidence](https://sha786muhammed.github.io/openWFN/science/validation-status/) and [limitations](https://sha786muhammed.github.io/openWFN/limitations/) before research use.

## Input support

Version 0.9.2 includes optional interoperability support and resource/export safety fixes.
See the [0.9.2 release notes](docs/releases/0.9.2.md).
Install `python -m pip install "openwfn[interop]==0.9.2"` for additional formats. The optional reader
is pinned to IOData 1.0.1 and has a [25-format ingestion matrix](docs/reference/formats-and-exports.md)
with [capability discovery](docs/reference/capabilities.md). Format ingestion
does not imply that every file has orbitals, density, or an applicable
analysis. The [cross-format validation](validation/interop/report.md) compares
five water representations from one originating calculation; it is not broad
independent scientific validation.

Gaussian formatted-checkpoint (`.fchk`) remains the preferred full-wavefunction
path. Gaussian `.chk` is a proprietary binary format; openWFN calls Gaussian's
separately installed `formchk` utility and does not decode it directly.

XYZ, MOL/SDF, and PDB inputs provide structure-only records. The optional
backend also reads structure, periodic, grid, and integral-only formats; use
`openwfn FILE capabilities` to check the actual data before analysis.

In openWFN 0.9.2, use `--input-format FORMAT_ID` when a
filename is ambiguous (for example, a GAMESS `.dat`). A structure without a
complete wavefunction gets a partial `summary`; it does not get inferred
orbitals, density, or electron counts. Mixed batches can use `--format-map`
and record unsupported files with reasons in the manifest. A batch exits
nonzero if any input fails or is unsupported. See the
[batch guide](docs/guides/batch-and-reports.md) for the exact contract.

```bash
openwfn calculation.chk formchk calculation.fchk
openwfn calculation.fchk convert --to sdf --output molecule.sdf
openwfn calculation.fchk density cube density.cube
```

## Documentation

### Output properties preview

Version 0.9.2 can extract source-reported properties from QC text
output through the optional cclib reader:

```bash
python -m pip install "openwfn[outputs]==0.9.2"
python -m openwfn.cli --format json calculation.out properties
```

Python exposes the same result through `openwfn.read_output(path)`. See the
[output properties preview](docs/output-properties.md) for units, provenance,
missing-data behavior and the current Experimental validation boundary.

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

Project policies: [Code of Conduct](CODE_OF_CONDUCT.md) ·
[Security](SECURITY.md) · [Maintainers](MAINTAINERS.md) ·
[Contributors](CONTRIBUTORS.md) · [Roadmap](ROADMAP.md)

## Citation and license

Cite the exact version used and the project repository; see the [citation guide](https://sha786muhammed.github.io/openWFN/citation/). openWFN is released under the [MIT License](LICENSE).

**Author:** Muhammed Shah Shaji
