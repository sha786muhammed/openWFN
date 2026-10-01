# Interoperability preview

This page describes the unreleased 0.9.0 source checkout. The last published
release documented here is 0.8.2. From the source checkout, install the
optional format reader with:

```bash
python -m pip install -e ".[interop]"
```

The base install still works without IOData. Gaussian FCHK continues through
the native parser, and existing FCHK commands keep their meaning. The
optional reader is pinned to `qc-iodata==1.0.1` and is used for formats without
a stronger native path. A `.chk` file still needs Gaussian's external
`formchk` converter.

## Inspect before analyzing

```bash
openwfn molecule.molden capabilities
openwfn molecule.wfx orbitals frontier
openwfn calculation.out summary
openwfn batch ./calculations --analyses summary,frontier --output-dir ./results
```

The [25-format matrix](reference/formats-and-exports.md) lists ingestion
paths and the components found in pinned fixtures. Run
[`capabilities`](reference/capabilities.md) on the actual file to see which
data and analyses are available. A program output containing geometry and
energy may have no complete wavefunction; openWFN then returns a structured
unsupported result rather than manufacturing orbital data.

The high-level Python `load(path)` API returns an `OpenWFNCalculation` whose
`.data` is an `OpenWFNData` container. Its structure, complete isolated
calculation, periodic cell, grids, integrals, and metadata are separate
optional components. The [Python API reference](reference/python-api.md)
explains migration from direct `.data` field access in older scripts.

## Evidence and boundaries

The format contract uses 25 redistribution-safe, checksum-pinned fixtures.
Five water wavefunction files derived from one project-owned FCHK are checked
against explicit geometry, orbital, population, and grid-density tolerances.
Separate constructed ORCA, Q-Chem, GAMESS, and CP2K examples check only
their available normalized fields. The
[cross-format report](https://github.com/sha786muhammed/openWFN/tree/main/validation/interop)
is a conversion-consistency regression, not independent confirmation across
programs, chemical systems, or experimental measurements. See
[limitations](limitations.md) before using a result in research.
