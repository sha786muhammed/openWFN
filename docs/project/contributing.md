# Contributing

Start with the repository [contribution guide](https://github.com/sha786muhammed/openWFN/blob/main/CONTRIBUTING.md).
It explains environment setup, tests, documentation and pull requests.
For scientific changes, include reference comparisons and use example data
you have permission to share.

Before starting, choose the matching GitHub issue form:

- a bug report for reproducible software behavior;
- a scientific discrepancy for numerical, unit, convention, or validation claims;
- a feature proposal for new behavior or format coverage.

Keep changes focused. Scientific work must include definitions, units,
tolerances, reference procedures, shareable fixtures, provenance, and explicit
limitations. External code or data requires compatible license terms and
preserved attribution.

After installing the repository in editable mode, run
`python scripts/check_repository.py --root .`. This read-only preflight checks
policy and attribution files, public text, generated package metadata, and the
editable installation. If it reports stale metadata, inspect ignored files with
`git status --ignored --short`, reinstall with
`python -m pip install --no-build-isolation -e .`, and run the preflight again.

Also read the repository's [Code of Conduct](https://github.com/sha786muhammed/openWFN/blob/main/CODE_OF_CONDUCT.md),
[maintainer policy](https://github.com/sha786muhammed/openWFN/blob/main/MAINTAINERS.md),
and [roadmap](https://github.com/sha786muhammed/openWFN/blob/main/ROADMAP.md).
