# Tests for openWFN

Run the full test suite with:

```bash
pytest -q
```

Install test dependencies with:

```bash
pip install -e .[test]
```

If you only want the released package for normal use, install:

```bash
pip install openwfn
```

Useful focused runs:

```bash
pytest tests/test_cli.py -q
pytest tests/test_geometry.py -q
```
