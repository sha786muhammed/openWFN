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

## Stable release 0.10.1

**openWFN 0.10.1** hardens the 0.10 everyday-QC release around reproducible
validation evidence and published-package verification without changing the
scientific numerical kernels. Install the exact release with
`python -m pip install "openwfn[interop,resources]==0.10.1"`.
See the [release notes](docs/releases/0.10.1.md).

The release includes [11 real molecular examples](examples/everyday-qc/README.md),
packages the same corpus with the wheel, and retains the
[Experimental coverage audit](docs/project/experimental-coverage.md).
Validated methods remain scoped to their documented reference evidence;
package stability does not change individual scientific validation labels.

| Capability | Scientific controls |
|---|---|
| Signed MO cubes, arbitrary MO/HOMO/LUMO, alpha/beta | AO/grid norm diagnostics, bounded chunks, input-hash cube comments |
| Mulliken/Löwdin MO composition | Named convention, atom/shell/angular partitions, raw norm and overlap conditioning |
| Spin-corrected Mayer bond orders | Total/spin conservation, density provenance, full matrix and filtered pairs |
| Orbital-energy DOS/PDOS | Gaussian sigma/range controls, spin channels, projection sum rules, CSV/JSON/PNG/SVG |

See the [design and roadmap](docs/project/everyday-qc-design.md),
[validation and limitations](docs/project/everyday-qc-validation.md), and
[method documentation](docs/science/dos-pdos.md).

## 0.11 development: native Hirshfeld

The 0.11 development branch adds native ordinary neutral-pro-atom Hirshfeld
populations and charges. The implementation is independently **Validated for a
named H/C/N/O all-electron scope**, not for arbitrary chemistry.

The fixed validation set contains water, methane, ammonia, carbon dioxide,
benzene, ethanol, ammonium, triplet oxygen, diffuse UHF OH, and the water dimer.
All ten cases pass both predeclared gates:

- maximum openWFN/HORTON-PART per-atom difference `<= 1.0e-3 e`;
- maximum openWFN standard-to-fine-grid per-atom shift `<= 5.0e-4 e`.

The observed worst external difference is about `1.27e-4 e`; the observed worst
grid-refinement shift is about `8.55e-5 e`. HORTON-PART is used only in the
validation workflow and is not an openWFN runtime dependency.

The scope is strict: unsupported elements, ECP/pseudopotential cases and
ghost-center ambiguity fail explicitly rather than using guessed pro-atom
densities. Ordinary unrestricted Hirshfeld uses the total density, and final
charges are not renormalized to hide integration residuals.

CLI:

```bash
openwfn calculation.fchk population hirshfeld
```

Python:

```python
from openwfn import load

calc = load("calculation.fchk")
result = calc.hirshfeld()
# equivalent convenience route:
result2 = calc.population("hirshfeld")
```

Authoritative development evidence is stored in
`validation/hirshfeld/reference-report.json`,
`validation/hirshfeld/convergence-report.json`, and `validation/manifest.json`.
See [validation status](docs/science/validation-status.md) and
[limitations](docs/limitations.md) before research use.

## Install

openWFN supports Python 3.10–3.13.

Install the stable release:

```bash
python -m pip install --upgrade openwfn
openwfn --version
```

Install the exact stable release when reproducing current published research:

```bash
python -m pip install openwfn==0.10.1
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
  --analyses summary,frontier,hirshfeld \
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

The default density spacing of **0.15 bohr** is an accuracy/performance tradeoff, not a universal convergence guarantee. Check the returned conservation status and converge spacing/padding for the system and property being reported. Native Hirshfeld likewise reports its numerical diagnostics and does not force final charge closure by renormalization.

## Capability map

| Area | Current capability | Status |
|---|---|---|
| Parsing and structure | FCHK records, molecular state, geometry, topology | Stable |
| Orbitals | Alpha/beta and spin-complete frontier energies and HOMO–LUMO information | Stable interface; fixture-backed regressions |
| Population | Mulliken and symmetric Löwdin populations and charges | Stable interface; conservation checked and fixture-scoped |
| Native Hirshfeld | Neutral-pro-atom populations and charges | Validated on the 0.11 development branch for the named H/C/N/O all-electron ten-case scope |
| Density | Total, alpha, beta, and spin integration and cube export | Validated only for named active fixtures/tolerances |
| Electrostatic potential | Nuclear and charge-model point ESP | Stable interface; special-case regressions included |
| Gaussian-integral electronic/total ESP | AO-density Coulomb integrals with independent references | Validated for the eleven-case set |
| Grid electronic/total ESP | Numerical Coulomb evaluation | Experimental |
| Automation | Versioned results, batch manifests, discovery, resume, JSON and CSV | Stable |
| Research reports | HTML/Markdown reports, tables, figures, and structures | Stable |
| Interactive workbench | Offline workspaces, surfaces and signed geometry readouts | Stable interface; eleven-molecule Chromium evidence; field diagnostics retained |
| Additional input formats | Optional IOData ingestion and file-specific capabilities | Stable fixture contract; requires the interop extra |
| QC output properties | Source-reported extraction with optional cclib | Experimental; not a complete wavefunction |
| Local MCP | Read-only stdio tools for selected registered analyses | Stable local interface; CLI/API/batch/report parity; no remote service |

“Validated” is deliberately scoped. Review the [validation evidence](https://sha786muhammed.github.io/openWFN/science/validation-status/) and [limitations](https://sha786muhammed.github.io/openWFN/limitations/) before research use.

## Input support

Version 0.10.1 includes optional interoperability support and resource/export safety fixes.
See the [0.10.1 release notes](docs/releases/0.10.1.md).
Install `python -m pip install "openwfn[interop]==0.10.1"` for additional formats. The optional reader
is pinned to IOData 1.0.1 and has a [25-format ingestion matrix](docs/reference/formats-and-exports.md)
with [capability discovery](docs/reference/capabilities.md). Format ingestion
does not imply that every file has orbitals, density, or an applicable
analysis.

Gaussian formatted-checkpoint (`.fchk`) remains the preferred full-wavefunction
path. Gaussian `.chk` is a proprietary binary format; openWFN calls Gaussian's
separately installed `formchk` utility and does not decode it directly.

XYZ, MOL/SDF, and PDB inputs provide structure-only records. The optional
backend also reads structure, periodic, grid, and integral-only formats; use
`openwfn FILE capabilities` to check the actual data before analysis.

A structure without a complete wavefunction gets a partial `summary`; it does
not get inferred orbitals, density, or electron counts. Mixed batches can use
`--format-map` and record unsupported files with reasons in the manifest.

```bash
openwfn calculation.chk formchk calculation.fchk
openwfn calculation.fchk convert --to sdf --output molecule.sdf
openwfn calculation.fchk density cube density.cube
```

## Documentation

### Output properties preview

Version 0.10.1 can extract source-reported properties from QC text output through
the optional cclib reader:

```bash
python -m pip install "openwfn[outputs]==0.10.1"
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

## Resource validation

The 0.11 development resource matrix contains **11 molecules × 10 workflows =
110 prescribed CLI commands**, adding native Hirshfeld to the 0.10.1 matrix.
The benchmark checks command completion, timeout, observed RSS and generated
output size. **Resource success does not establish scientific validation.**
Capability-specific status comes from the separate validation evidence and
result diagnostics.

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

Development resource checks and their measured scope are documented in
[Runtime and resource validation](docs/project/resource-validation.md).
