# Capability discovery

These commands describe the unreleased interoperability branch. In a source
checkout, use `python -m pip install -e ".[interop]"`; after a release that
includes this feature, the package-index install will be:

```bash
python -m pip install "openwfn[interop]"
```

In a checkout of this branch, inspect the file before analysis:

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

Only one record is ingested from a multi-record file. Periodic structures,
stored volumetric grids, and FCIDUMP integrals remain distinct canonical
components; the molecular frontier/population/density methods do not become
available merely because a file has a grid or integrals. See the
[format matrix](formats-and-exports.md) and [limitations](../limitations.md).
