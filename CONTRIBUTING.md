# Contributing to openWFN

openWFN welcomes focused fixes, tests, documentation, parsers, and scientific
methods that stay within the project's stated capability boundaries. By
participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

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

## Run the checks

```bash
python -m ruff check src tests scripts
python -m pytest --strict-markers
python scripts/run_validation.py
python scripts/run_external_benchmarks.py --repository-only
python scripts/check_docs.py --root .
python scripts/sync_release_metadata.py --check
python -m mkdocs build --strict
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
