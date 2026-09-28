# Tests for openWFN

Create a clean development environment from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
python scripts/check_repository.py --root .
```

Run a focused test while developing:

```bash
python -m pytest -q tests/test_cli.py
python -m pytest -q tests/test_geometry.py
```

Before opening a pull request, run the complete suite:

```bash
python -m pytest --strict-markers
```

The repository preflight is read-only. If it finds stale source-tree package
metadata or an editable install from another checkout, inspect and refresh it:

```bash
git status --ignored --short
python -m pip install --no-build-isolation -e .
python scripts/check_repository.py --root .
```

For normal use of the released package, install with `python -m pip install
openwfn` instead of using this development setup.
