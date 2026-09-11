# Validation status and evidence

openWFN separates implementation availability from scientific confidence.

- **Stable** — supported interface with tests for expected behavior.
- **Validated** — compared against defined numerical invariants or reference expectations for the named validation set.
- **Experimental** — available for investigation, but evidence is not broad enough for routine research claims.
- **Unsupported** — required data, method, or verification is absent.

## Active v0.7 validation set

The provenance-backed fixtures currently cover water, methane, and ammonia. The validation suite evaluates nine metrics across these cases, including geometry and electron-density conservation. Run it from a source checkout:

```bash
python scripts/run_validation.py
```

Passing these cases establishes regression evidence for those fixtures and tolerances; it does not prove accuracy for every molecule, basis, charge state, or spin state.

## Coverage still needed

Broader cases such as carbon dioxide, triplet oxygen, ethanol, water dimers, benzene, diffuse/polarized basis behavior, and transition-metal chemistry require legally shareable, provenance-documented fixtures and explicit acceptance criteria. Until added, extrapolation is the researcher's responsibility.

## Reproduce the software checks

```bash
python -m pytest
python -m ruff check .
python scripts/check_docs.py --root .
python -m mkdocs build --strict
```

Read [limitations](../limitations.md) before publication and cite the exact version used.

