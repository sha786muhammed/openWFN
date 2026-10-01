# Capability discovery

These commands are available in openWFN 0.9.1. For IOData-backed formats, install:

```bash
python -m pip install "openwfn[interop]==0.9.1"
```

Inspect the file before analysis:

```bash
openwfn molecule.molden capabilities
openwfn molecule.wfx orbitals frontier
openwfn calculation.out summary
openwfn batch ./calculations --analyses summary,frontier --output-dir ./results
```

Run `capabilities` before a batch when input files may contain different
records. It reports the detected format, backend and version, each component
capability, and which registered analyses have their requirements met. Use
`openwfn --format json FILE capabilities` for automation. In Python,
`load(path).capabilities()` returns the same inferred component states.

`available` means the relevant data are directly present. `derived` means
openWFN can calculate the component from present data; for example, AO overlap
may be derived from a supported basis. `missing` means the file does not
provide it. These are the states currently returned for listed components.
`unsupported` is reserved in the capability type for unrecognized requirements;
an analysis lacking required components returns a structured Unsupported
result. Capability states describe what can be attempted, not an independent
accuracy certification. A `missing` wavefunction must not be filled in from
atomic electron counts alone.

For ambiguous inputs such as GAMESS `.dat`, use
`openwfn --input-format gamess FILE capabilities` or
`load(path, format_hint="gamess")`. `doctor` includes the same normalized
capability and analysis report. An available `summary` requirement means the
file has structure; a geometry-only or periodic summary is still marked
`partial` because electronic fields are unavailable.

Only one record is ingested from a multi-record file. Periodic structures,
stored volumetric grids, and FCIDUMP integrals remain distinct canonical
components; the molecular frontier/population/density methods do not become
available merely because a file has a grid or integrals. See the
[format matrix](formats-and-exports.md) and [limitations](../limitations.md).

## Grid resource safety

Version 0.9.1 rejects molecular grids above 2,000,000 points before allocating
coordinate arrays. The limit applies to density integration, cube export and
grid-based ESP. A rejected request must be retried with larger spacing or smaller
padding; openWFN does not change either setting automatically. Smaller padding
can omit density tails, so check conservation and grid convergence afterwards.
AO evaluation chunks also shrink for larger bases. These bounds reduce memory
use but are not a guarantee that every calculation fits on every machine.
