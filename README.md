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

- **Analyze** molecular structure, orbitals, electron density, atomic populations, electrostatic potential, vibrational modes/spectra, excited states, and derived properties.
- **Automate** with stable CLI commands, a typed Python API, structured results, resumable batches, and JSON/CSV exports.
- **Validate** using explicit capability status, parser provenance, transformations, numerical controls, and fixture-backed evidence.
- **Publish** durable reports, figures, cube files, structures, and batch manifests.

## Stable release 0.11.0

**openWFN 0.11.0** integrates native Hirshfeld analysis, vibrational spectroscopy,
and method-general excited-state/UV–Vis post-processing into the public stable
package. Install the exact release with
`python -m pip install "openwfn[interop,resources]==0.11.0"`.
See the [release notes](docs/releases/0.11.0.md).

Stable package status does not make every scientific analysis Validated. The
machine-readable [validation manifest](validation/manifest.json) remains the
authoritative capability-status registry:

- ordinary Hirshfeld populations/charges are **Validated** only for the named
  H/C/N/O all-electron ten-case scope and fixed tolerances;
- vibrational spectroscopy remains **Experimental** pending independent external
  spectroscopy validation;
- excited-state and UV–Vis analyses remain **Experimental** pending named
  independent cross-program/method validation.

The release retains the versioned 11-molecule everyday-QC corpus and runs a
110-command bounded workflow/resource matrix against both the built wheel and
the package downloaded back from public PyPI.

## Hirshfeld population analysis

```bash
openwfn calculation.fchk population hirshfeld
```

Ordinary neutral-pro-atom Hirshfeld analysis reports closure diagnostics and does
not renormalize final charges to hide numerical residuals. Unsupported elements,
ECP/pseudopotential ambiguity, and ghost-center ambiguity fail explicitly rather
than using guessed pro-atoms.

## Vibrational spectroscopy

```bash
openwfn frequency.log vibrations
openwfn frequency.log spectra ir --fwhm 20 --points 2001 --export ir.csv
openwfn frequency.log spectra raman --export raman.svg
```

Gaussian Raman activities are preserved as source activities and are not
silently converted to experimental Raman intensities. Imaginary frequencies
remain signed in source data and are excluded from broadened physical curves
with explicit warnings. See the
[vibrational spectroscopy method page](docs/science/vibrational-spectroscopy.md).

## Excited states and UV–Vis

```bash
openwfn excited.log excited states
openwfn excited.log excited state 1
openwfn excited.log excited dipoles
openwfn excited.log spectra uvvis --fwhm-ev 0.20 --export uvvis.svg
```

The typed excited-state layer supports the implemented Gaussian, ORCA, and
Q-Chem source adapters while preserving source method detail and explicit
amplitude conventions. UV–Vis broadening is performed in energy space and the
wavelength-domain curve uses the energy-to-wavelength Jacobian rather than
relabeling the same y-array. Missing oscillator strengths are not treated as
zero; dark `f=0` states remain valid source states. See
[Excited states and UV–Vis](docs/science/excited-states-uvvis.md).

## Install

openWFN supports Python 3.10–3.13.

Install the stable release:

```bash
python -m pip install --upgrade openwfn
openwfn --version
```

Install the exact release when reproducing research:

```bash
python -m pip install openwfn==0.11.0
```

## First analysis

```bash
openwfn examples install ./openwfn-examples
openwfn ./openwfn-examples/water.fchk doctor
openwfn ./openwfn-examples/water.fchk summary
openwfn ./openwfn-examples/water.fchk orbitals frontier
```

The same install command also places the versioned 11-molecule release corpus in
`./openwfn-examples/everyday-qc/` for reproducible workflow checks.

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
| Hirshfeld population | Ordinary neutral-pro-atom H/C/N/O populations/charges | Validated only for the named ten-case all-electron scope |
| Density | Total, alpha, beta, and spin integration and cube export | Validated only for named active validation fixtures and tolerances |
| Electrostatic potential | Nuclear and charge-model point ESP | Stable interface; special-case regressions included |
| Gaussian-integral electronic/total ESP | AO-density Coulomb integrals with independent references | Validated for the eleven-case set |
| Grid electronic/total ESP | Numerical Coulomb evaluation | Experimental |
| Vibrational spectroscopy | Native Gaussian modes, IR intensity, Raman activity, broadened curves, source vectors | Experimental; independent validation pending |
| Excited states / UV–Vis | Gaussian/ORCA/Q-Chem source states, dipoles, oscillator-strength sticks and broadened profiles | Experimental; independent cross-program validation pending |
| Automation | Versioned results, batch manifests, discovery, resume, JSON and CSV | Stable |
| Research reports | HTML/Markdown reports, tables, figures, structures, vibrational/excited-state sections | Stable interface; individual analysis status retained |
| Interactive workbench | Offline workspaces, surfaces, signed geometry readouts, Vibrations and Excited States workspaces | Stable interface; displayed scientific status retained |
| Additional input formats | Optional IOData ingestion and file-specific capabilities | Stable fixture contract; requires the interop extra |
| QC output properties | Source-reported extraction with optional cclib | Experimental; not a complete wavefunction |
| Local MCP | Read-only stdio tools for registered analyses with validated scalar parameters | Stable local interface; no remote service |

“Validated” is deliberately scoped. Review the [validation evidence](https://sha786muhammed.github.io/openWFN/science/validation-status/) and [limitations](https://sha786muhammed.github.io/openWFN/limitations/) before research use.

## Input support

Version 0.11.0 includes optional interoperability support and the release safety
contracts established on the 0.10 line. See the
[0.11.0 release notes](docs/releases/0.11.0.md).
Install `python -m pip install "openwfn[interop]==0.11.0"` for additional formats.
The optional reader is pinned to IOData 1.0.1 and has a
[25-format ingestion matrix](docs/reference/formats-and-exports.md) with
[capability discovery](docs/reference/capabilities.md). Format ingestion does
not imply that every file has orbitals, density, or an applicable analysis.
The [cross-format validation](validation/interop/report.md) compares five water
representations from one originating calculation; it is not broad independent
scientific validation.

Gaussian formatted-checkpoint (`.fchk`) remains the preferred full-wavefunction
path. Gaussian `.chk` is a proprietary binary format; openWFN calls Gaussian's
separately installed `formchk` utility and does not decode it directly.

XYZ, MOL/SDF, and PDB inputs provide structure-only records. The optional
backend also reads structure, periodic, grid, and integral-only formats; use
`openwfn FILE capabilities` to check the actual data before analysis.

In openWFN 0.11.0, use `--input-format FORMAT_ID` when a filename is ambiguous
(for example, a GAMESS `.dat`). A structure without a complete wavefunction gets
a partial `summary`; it does not get inferred orbitals, density, or electron
counts. Mixed batches can use `--format-map` and record unsupported files with
reasons in the manifest. A batch exits nonzero if any input fails or is
unsupported. See the [batch guide](docs/guides/batch-and-reports.md) for the
exact contract.

```bash
openwfn calculation.chk formchk calculation.fchk
openwfn calculation.fchk convert --to sdf --output molecule.sdf
openwfn calculation.fchk density cube density.cube
```

## Documentation

### Output properties preview

Version 0.11.0 can extract source-reported properties from QC text output through
the optional cclib reader:

```bash
python -m pip install "openwfn[outputs]==0.11.0"
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
- [Vibrational spectroscopy](docs/science/vibrational-spectroscopy.md)
- [Excited states and UV–Vis](docs/science/excited-states-uvvis.md)
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
