# Reproducible research with openWFN

Keep the input, software version, command, settings and output together.
openWFN can save JSON results and reports. You still need to record how the
original calculation was produced and explain what the results mean.

## Minimum research record

Record:

- the source and checksum of the input file;
- electronic-structure method, basis set, charge, multiplicity, and job type;
- `openwfn --version` and the complete command;
- grid spacing and padding for numerical density or ESP work;
- capability status and known limitations at the software version used;
- unedited output plus any downstream processing scripts.

```bash
openwfn --version
shasum -a 256 molecule.molden
openwfn --format json --output summary.json molecule.molden summary
```

## Save results without replacing earlier work

Use JSON or CSV for subsequent computation and preserve terminal tables only for reading. Do not silently overwrite results: openWFN requires `--overwrite` when an output already exists. Reports capture the invoked command and can combine selected analyses.

```bash
openwfn molecule.molden report build analysis.html \
  --analyses summary,frontier,mulliken,lowdin
```

## Numerical convergence

Density integrations and grid-derived ESP depend on spacing and padding. Repeat calculations with tighter spacing and larger padding until the scientifically relevant digits are stable. Report the tested settings, not only the final value.

## Citation

Cite the openWFN version used, along with the program and method that produced
your input. Use the [citation guide](../citation.md) for the software citation.
