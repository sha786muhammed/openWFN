# Research workflow checks

These examples exercise post-processing, including unavailable properties. They
do not establish the chemical accuracy of the source method or basis set.

- [Input-family examples](file-formats.md): use existing fixtures without duplicating them.
- [Biphenyl](biphenyl/README.md): a larger conjugated wavefunction and independent numerical comparisons.
- [Source spectroscopy](spectroscopy/README.md): nine larger Gaussian, ORCA and Q-Chem outputs with printed-value checks.
- [Real-space fields](real-space/README.md): hydrogen, ethylene and biphenyl fields plus independent local bond-point checks.
- [Property workflows](property-workflows.md): choose the required input records, settings and output for each calculation family.

## Start with an input

From the repository root:

```bash
openwfn examples/research-workflows/biphenyl/biphenyl.molden capabilities
openwfn examples/research-workflows/biphenyl/biphenyl.molden open
```

In guided mode, select **All calculation methods and requirements** to inspect
the registered methods, including those unavailable from your file. Review the
settings before running. A Molden wavefunction without frequency records cannot
provide IR or Raman data. The missing-record message is an expected outcome.

## Run a repeatable coverage review

```bash
python scripts/review_workflows.py --output /tmp/openwfn-coverage.json
python scripts/review_workflows.py \
  examples/research-workflows/biphenyl/biphenyl.molden \
  --output /tmp/openwfn-biphenyl-coverage.json
```

Use new output paths for each run. The default review covers the pinned
interoperability fixtures and everyday molecular examples. It includes every
registered analysis, a coarse density integration, an ESP point and a geometry
summary. It retains full result records and compact CLI previews.

The outcomes have different meanings:

- `calculated`: the bounded operation returned success; not an independent numerical validation.
- `partial`: inspect its warning and diagnostics before using the values.
- `unavailable`: the input lacks required records.
- `unsupported-scope`: the method lacks a reference for this particular case.
- `failed`: investigate the recorded error; do not treat it as missing data automatically.

Density uses coarse 0.4-bohr spacing and 4-bohr padding for this workflow probe.
QTAIM uses two explicit seeds, eight iterations and no bond paths. These
settings do not establish convergence or a complete molecular topology.
Real-space fields use explicit bohr coordinates. ESP points use angstrom.
Open-shell ELF/LOL checks explicitly select alpha rather than assuming a
spin-summed definition.

## Independent comparisons

PySCF is a validation dependency, not required for normal openWFN use:

```bash
python -m pip install pyscf==2.14.0
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python -m scripts.validate_research_examples --output-dir /tmp/openwfn-biphenyl-reference
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python scripts/validate_everyday_pyscf.py --output-dir /tmp/openwfn-everyday-reference
```

Use an empty output directory. See the biphenyl example for its exact recipe,
checksums, dependencies and reference comparisons. Tests under
`tests/validation/` and `tests/unit/` contain additional method-specific checks;
the coverage report does not replace those checks.
