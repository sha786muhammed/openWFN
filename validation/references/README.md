# Validation references

The registry in `validation/manifest.json` is authoritative. Active inputs remain under `examples/` to avoid duplicated scientific files. Every active entry records its SHA-256 checksum, origin, known generation information, method, basis, redistribution status, expected values, and tolerances.

Existing fixtures predate the validation registry, so their exact Gaussian version and invocation are not known. This limitation is retained explicitly. Pending cases are named in the manifest but are not treated as passing references and contain no fabricated numerical values.

Run `python scripts/run_validation.py` to create `validation/results.json` and `validation/report.md`.
