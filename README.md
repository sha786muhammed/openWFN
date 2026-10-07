<p align="center">
  <img src="docs/assets/images/openwfn-brand.svg" width="360" alt="openWFN">
</p>

<p align="center"><strong>Wavefunction analysis, made reproducible.</strong></p>

<p align="center">Wavefunction post-processing for quantum chemistry. Use the same scientific engine from the CLI, Python, MCP or terminal chat.</p>

<p align="center">
  <a href="https://pypi.org/project/openwfn/"><img alt="PyPI" src="https://img.shields.io/pypi/v/openwfn?label=PyPI&color=4051b5&cacheSeconds=300"></a>
  <a href="https://github.com/sha786muhammed/openWFN/actions/workflows/tests.yml"><img alt="Tests" src="https://github.com/sha786muhammed/openWFN/actions/workflows/tests.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-4051b5"></a>
</p>

openWFN reads supported quantum-chemistry files and returns analysis results
with units, warnings and source provenance. Analyze individual calculations and
high-throughput collections without changing the scientific engine between interfaces.

This branch prepares **0.12.0**. The published release is still **0.11.0** until
[release checks](docs/releases/0.12.0.md) pass. The new guided/chat features and
base-install readers require this checkout before publication.

## Install and inspect a file

Published package:

```bash
python -m pip install --upgrade openwfn
openwfn --version
```

For this release-preparation checkout, use a separate environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

The prepared release includes format readers, output extraction, Python API,
local MCP and terminal chat in the normal installation. No model weights,
Gaussian utilities or public servers are installed automatically.

```bash
openwfn molecule.molden open
openwfn molecule.molden capabilities
openwfn molecule.fchk summary
openwfn --format json molecule.fchk analyze
```

Guided mode offers workflows supported by the selected file. It shows settings,
units and atom numbering, checks grid size, confirms save paths, and can show the
equivalent command. Scripts should use explicit commands such as `summary`;
file-only non-terminal invocations now return a bounded overview.

## Supported input families

| Files | Available data determine the analyses |
| --- | --- |
| `.fchk`, `.fch`, `.molden`, `.molden.input`, `.wfn`, `.wfx`, `.mwfn`, `.mkl` | Wavefunction records, basis, orbitals and electronic state |
| `.cube`, `.cub` | Stored scalar grids, axes and units |
| Gaussian, ORCA and Q-Chem `.log` / `.out` | Source-reported properties and supported spectroscopy records |
| `.xyz`, `.pdb`, `.mol`, `.sdf` | Molecular structure and supported formal-charge records |

Binary `.chk` is a proprietary binary format. Conversion needs Gaussian's
separately installed `formchk`; pip does not supply it. A parser cannot create
wavefunction data that the input does not contain. See the
[format contract](docs/reference/formats-and-exports.md) for variants and limitations.

## Scientific analyses

The shared engine provides geometry, frontier orbitals, MO composition/cubes,
Mulliken/Löwdin/Hirshfeld populations, Mayer bond orders, DOS/PDOS, density checks,
ESP, supported vibrational/excited-state properties and conservative NTO analysis.
It also exposes bounded QTAIM critical-point searches and ELF/LOL/NCI fields.

Population analysis uses source-reported effective nuclear charges for ECP and
ghost centers; conservation failures return partial results with warnings.
The direct density default is 0.15 bohr spacing, not a convergence guarantee.
Use coarser settings for exploration and check convergence before reporting values.

```bash
openwfn molecule.fchk orbitals frontier --spin all
openwfn molecule.fchk population mulliken
openwfn molecule.fchk density integrate --spacing 0.3 --padding 6
openwfn calculation.out properties
```

Scientific status is separate from package status. Hirshfeld and other Validated
methods are validated only for their named scopes. Spectroscopy, output
extraction and the newer real-space tools retain their documented Experimental
boundaries. QTAIM basin integration is not included.

Conservation errors and source warnings stay visible. Unknown charge/spin is
not guessed; normal job termination is not proof of optimization convergence.
Density settings require a convergence study for the intended property.
[Methods](docs/methods.md), [validation](docs/science/validation-status.md) and
[limitations](docs/limitations.md) explain those boundaries.

## Python, collections and saved results

```python
from openwfn import load

calculation = load("molecule.molden")
print(calculation.capabilities())
result = calculation.analyze("frontier-all")
print(result.as_dict())
```

```bash
openwfn batch ./calculations \
  --analyses summary,frontier --output-dir ./results --resume

openwfn --format json --output summary.json molecule.fchk summary
```

JSON preserves the complete result envelope. HTML/Markdown reports, CSV tables,
figures, cube files and the offline workbench are export options, not
requirements for Linux or headless workflows.

## Scientific assistant and MCP

Configure an existing local model; openWFN does not train or download one:

```bash
openwfn molecule.molden chat --model qwen3:8b
openwfn chat
```

The model selects a tool request. openWFN checks capabilities and settings and
renders the values and explanations from the scientific result. Remote model
use requires explicit permission. See [assistant setup](docs/assistant.md).

The normal installation also includes a read-only local MCP server:

```bash
python -m openwfn.mcp_server --data-root ./inputs
```

That process waits for an MCP client on stdio; it is not a public HTTP service.
[MCP setup](docs/mcp.md) describes client configuration, confirmation and
resource limits. External hosts control their own generated prose.

## Documentation and contributing

- [First analysis](docs/start/first-analysis.md)
- [CLI reference](docs/reference/cli.md) and [Python API](docs/reference/python-api.md)
- [Citation](docs/citation.md)
- [Contributor guide](CONTRIBUTING.md) and [security policy](SECURITY.md)
- [Release history](docs/project/release-history.md)

The package includes redistributable examples:

```bash
openwfn examples install ./openwfn-examples
openwfn ./openwfn-examples/water.fchk summary
```

Keep the input checksum, package version, command/settings and complete result
with your work. Do not post unpublished calculations, credentials or personal
paths in public issues. Project-owned code is MIT licensed; dependency terms
are listed in [third-party notices](THIRD_PARTY_NOTICES.md).
