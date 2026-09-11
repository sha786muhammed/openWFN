# Reproducible research with openWFN

A reproducible result preserves the input identity, software version, command, numerical controls, and output. openWFN provides machine-readable output and self-contained reports, but the researcher remains responsible for calculation provenance and interpretation.

## Minimum research record

Record:

- the source and checksum of the input FCHK;
- electronic-structure method, basis set, charge, multiplicity, and job type;
- `openwfn --version` and the complete command;
- grid spacing and padding for numerical density or ESP work;
- capability status and known limitations at the software version used;
- unedited output plus any downstream processing scripts.

```bash
openwfn --version
shasum -a 256 molecule.fchk
openwfn --format json --output summary.json molecule.fchk summary
```

## Prefer explicit, immutable artifacts

Use JSON or CSV for subsequent computation and preserve terminal tables only for reading. Do not silently overwrite results: openWFN requires `--overwrite` when an output already exists. Reports capture the invoked command and can combine selected analyses.

```bash
openwfn molecule.fchk report build analysis.html \
  --analyses summary,frontier,mulliken,lowdin
```

## Numerical convergence

Density integrations and grid-derived ESP depend on spacing and padding. Repeat calculations with tighter spacing and larger padding until the scientifically relevant digits are stable. Report the tested settings, not only the final value.

## Citation

Cite the exact openWFN release and repository, along with the electronic-structure software and method used to generate the checkpoint. Copy the current metadata from the [citation guide](../citation.md).
