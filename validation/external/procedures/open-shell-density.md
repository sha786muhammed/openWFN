# Open-shell WFX/WFN density comparison

This procedure checks three unrestricted molecular wavefunctions from the IOData
test corpus at commit `9f7e800fc414b086d677b5f2882dd0c1dfa919f3`. The exact
paths, SHA-256 hashes, expected occupation counts, grid settings, points, and
tolerances are in `validation/external/manifest.json`. The inputs remain in an
external checkout; they are not redistributed with openWFN.

Use a separate environment with `qc-iodata==1.0.1` and `qc-gbasis==0.1.0`:

```bash
python -m pip install -e '.[test,interop]' 'qc-gbasis==0.1.0'
python scripts/run_external_benchmarks.py \
  --input-root "$OPENWFN_BENCHMARK_INPUTS" \
  --output-dir /tmp/openwfn-external
```

The runner verifies each input hash before analysis. For pointwise checks, it
uses IOData's orbital coefficients and occupations to form separate alpha and
beta AO density matrices. GBasis constructs its own basis representation and
evaluates the channel densities at the five fixed points in bohr. openWFN
independently evaluates its normalized density matrices at the same points.
Spin density is alpha minus beta; GBasis rejects a signed spin matrix as a
nonnegative density, so the reference subtracts its separately evaluated
alpha and beta values. The metric is the maximum absolute difference in
electron/bohr³; the limit is `2e-9` for each channel.

The grid checks integrate alpha, beta, and spin density at the *fixed* spacing
and padding in the manifest and compare against the source occupation counts.
These checks detect regressions at those settings. Their tolerances were set
after exploratory Ubuntu 22.04 runs; they are not pre-registered accuracy targets or
proof of grid convergence. In particular, O₂ alpha and beta integrals each
miss the occupation count by about 0.032 electrons at 0.20 bohr, while their
spin difference misses by only 0.000081 electrons because errors cancel.
Tightening to 0.15 bohr did not monotonically improve O₂'s channel integrals.
Do not use the fixed-grid O₂ numbers as publication-grade quantitative density
evidence without a separate convergence study.

Both pointwise paths share the IOData parser and source orbital data. The
comparison tests the independent AO/density evaluation implementations, not
the correctness of the underlying electronic-structure calculation, every
point in space, or every input producer. Retain the JSON report, environment
versions, source commit, and input checksums when reporting these results.
