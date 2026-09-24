# Validation status and evidence

openWFN separates implementation availability from scientific confidence.

- **Stable** — supported interface with tests for expected behavior.
- **Validated** — compared against defined numerical invariants or reference expectations for the named validation set.
- **Experimental** — available for investigation, but evidence is not broad enough for routine research claims.
- **Unsupported** — required data, method, or verification is absent.

## Internal regression and invariants

The provenance-backed fixtures currently cover water, methane, and ammonia. The validation suite evaluates nine metrics across these cases, including geometry and electron-density conservation. Run it from a source checkout:

```bash
python scripts/run_validation.py
```

Passing these cases establishes regression evidence for those fixtures and tolerances; it does not prove accuracy for every molecule, basis, charge state, or spin state.

## Independent parser comparisons

The external registry compares openWFN with `qc-iodata==1.0.1` using identical FCHK
inputs, immutable source commits, SHA-256 checksums, and explicit tolerances.

| Evidence | Active cases | Metrics | Status |
|---|---|---|---|
| Independent FCHK parsing | water, benzene, LiH, oxygen (pure and Cartesian), helium high-l | total energy and alpha frontier orbitals | 24 comparisons passing |
| Independent producer parser | acetylene from Psi4 | parser fields | qc-iodata 1.0.1 limitation: cannot parse one adjacent fixed-width exponent pair |

The parser comparison verifies extraction of the listed values. It does not independently
validate population or density algorithms. Reproduce the complete external matrix with:

```bash
python scripts/run_external_benchmarks.py \
  --input-root "$OPENWFN_BENCHMARK_INPUTS" \
  --output-dir /tmp/openwfn-external
```

See the [registry procedure](https://github.com/sha786muhammed/openWFN/blob/main/validation/external/procedures/qc-iodata.md) for
source commits, selection conventions, and tolerances.

## Independent analysis comparisons

Multiwfn `3.8(dev)` (2024-10-24) independently agrees with openWFN for restricted water,
unrestricted LiH, and Psi4-produced acetylene. Eleven comparisons pass: total energy, alpha frontier orbital energies,
Mulliken atomic charges, and Löwdin atomic charges, with tolerances based only on the
reference program's printed precision.

| Case | Wavefunction | Compared metrics | Status |
|---|---|---|---|
| Water | Restricted | HOMO, LUMO, Mulliken charges, Löwdin charges | 4 passing |
| LiH | Unrestricted doublet | Alpha HOMO, alpha LUMO, Mulliken charges, Löwdin charges | 4 passing |
| Acetylene | Restricted, Psi4 producer | Total energy, HOMO, LUMO | 3 passing |

The evidence records include binary, settings, input, procedure, and transcript hashes,
plus NASAKY platform metadata. See the [Multiwfn procedure](https://github.com/sha786muhammed/openWFN/blob/main/validation/external/procedures/multiwfn.md). These comparisons validate only the named metrics and fixtures; they do not establish accuracy for every chemical system.

## Coverage still needed

Broader cases such as carbon dioxide, triplet oxygen with confirmed spin metadata,
ethanol, water dimers, diffuse/polarized basis behavior, and transition-metal chemistry
require legally shareable, provenance-documented fixtures and explicit acceptance
criteria. Until added, extrapolation is the researcher's responsibility.

## Reproduce the software checks

```bash
python -m pytest
python -m ruff check .
python scripts/check_docs.py --root .
python -m mkdocs build --strict
```

Read [limitations](../limitations.md) before publication and cite the exact version used.
