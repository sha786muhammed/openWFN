# Interoperability

Use supported wavefunction files, grids, structures and calculation outputs
with the same analysis engine. openWFN uses built-in readers or the included
`qc-iodata==1.0.1` reader. Binary Gaussian `.chk` conversion needs the separately
installed `formchk` utility.

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

In Python, `load(path)` returns an `OpenWFNCalculation`. Its `.data` contains
the records found in the file. Structure, wavefunction, periodic-cell, grid and
integral data remain separate: having one does not imply the others are present.
See the [Python API reference](reference/python-api.md) for field access.

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
