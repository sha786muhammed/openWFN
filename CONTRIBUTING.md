# Contributing to openWFN

openWFN welcomes focused fixes, tests, documentation, parsers, and scientific
methods that stay within the project's stated capability boundaries. By
participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Find a useful first contribution

You do not need to implement a new scientific method to help. Start with a
small, reproducible improvement:

| Your background | A useful starting point |
| --- | --- |
| New user | Follow the [first-analysis tutorial](docs/start/first-analysis.md) and report an unclear step or unexpected result. |
| Computational chemist | Compare a documented analysis with an independent reference; include the input provenance, conventions and tolerances. |
| Python developer | Reproduce a parser or interface issue with a minimal fixture, then propose a focused fix. |
| Documentation contributor | Improve an example, clarify a limitation or check a command against the current release. |

[Browse issues](https://github.com/sha786muhammed/openWFN/issues) or
[propose a contribution](https://github.com/sha786muhammed/openWFN/issues/new/choose).
For a substantial method, parser or interface change, describe the scientific
problem and proposed scope in an issue before beginning implementation. Share
only inputs you have permission to redistribute.

## Set up a clean environment

```bash
git clone https://github.com/sha786muhammed/openWFN.git
cd openWFN
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test,docs]"
```

Use a focused branch. Do not commit virtual environments, caches, build output,
coverage files, generated package metadata, or research data.

## Repository map

| Location | Purpose |
| --- | --- |
| `src/openwfn/analysis/` | Scientific methods and the shared analysis registry |
| `src/openwfn/parsers/`, `adapters/` | Native readers and normalized interoperability |
| `src/openwfn/api.py`, `cli.py`, `assistant*.py`, `mcp_server.py` | Public interface boundaries |
| `src/openwfn/exporters/`, `workbench/`, `reporting.py` | Result exports and presentation |
| `tests/` | Interface, parser, numerical and regression tests |
| `validation/` | Named references, manifests and comparison evidence |
| `docs/` | Current user documentation and historical release notes |
| `scripts/` | Repository, validation, distribution and release checks |

## Run the checks

```bash
python scripts/check_repository.py --root .
python -m ruff check src tests scripts
python -m pytest --strict-markers
python scripts/run_validation.py
python scripts/run_external_benchmarks.py --repository-only
python scripts/check_docs.py --root .
python scripts/sync_release_metadata.py --check
python -m mkdocs build --strict
```

The repository preflight checks required policy and attribution files, public
text for private-machine or internal-tool details, source-tree package metadata,
and the active editable install. It only reports findings; it never deletes or
rewrites files. If it reports stale generated metadata or an editable install
from another checkout, inspect the ignored files and refresh this environment:

```bash
git status --ignored --short
python -m pip install --no-build-isolation -e .
python scripts/check_repository.py --root .
```

Run the focused test first while developing, then the complete suite before a
pull request. Add a failing regression test before changing behavior.

## Scientific changes

A scientific claim needs reviewable evidence. Include:

- the definition, convention, equations, expected value, units, and tolerance;
- the reference procedure and independently generated comparison where possible;
- a minimal shareable fixture, or a synthetic substitute when the real input is
  confidential;
- source program, version, method, basis, charge, multiplicity, and numerical
  controls when applicable;
- supported and unsupported cases, warnings, and capability status;
- fixture origin, transformation history, and redistribution permission.

Do not replace a reference value merely to make a test pass. Explain any
difference and establish why the new value is authoritative.

Parser changes must cite the producer documentation or format specification.
Fixtures copied from another project require compatible license terms and
preserved attribution. Do not copy an external implementation into openWFN;
write project-owned code from documented methods and permitted references.

## Documentation and provenance

Update user documentation when commands, outputs, limitations, or status change.
Commands must run from the location stated. New examples and public assets need
source, license, checksum, and known transformation details; record unavailable
historical fields as `not recorded` rather than inferring them.

## Pull requests

Keep each pull request to one logical change. Describe the problem, user impact,
scientific impact, limitations, tests run, documentation changed, provenance,
and license review. Complete the repository pull-request checklist. A passing
test suite is required but does not replace scientific or maintainership review.

Contributions are distributed under the project's [MIT License](LICENSE). See
[MAINTAINERS.md](MAINTAINERS.md) for review and release authority.
