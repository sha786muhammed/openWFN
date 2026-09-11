# Contributing

Contributions are welcome in parsing, scientific methods, validation fixtures, documentation, usability, and testing.

## Development setup

```bash
git clone https://github.com/sha786muhammed/openWFN.git
cd openWFN
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test,docs]"
```

## Quality checks

```bash
python -m pytest
python -m ruff check .
python scripts/run_validation.py
python scripts/check_docs.py --root .
python -m mkdocs build --strict
```

Add tests before changing behavior. Scientific features need equations, units, assumptions, failure modes, reference evidence, and a declared capability status. New fixtures must have redistribution permission and provenance.

## Documentation standard

Examples must run against the current CLI, equations must render with `$$` delimiters, internal links must resolve, and no private path or credential may enter public history. Write for researchers, students, and developers: define a concept before relying on it.

## Pull requests

Keep changes focused, describe user and scientific impact, list verification performed, and identify any limitations. A passing test suite is required but does not replace review of scientific assumptions.

