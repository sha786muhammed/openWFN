# openWFN Examples

The `examples/` directory contains small reference molecules you can use to test
the CLI quickly without preparing your own Gaussian files first.

If you installed `openwfn` from PyPI, clone the repository as well if you want
to use these example files directly:

```bash
git clone https://github.com/sha786muhammed/openWFN.git
cd openWFN
```

Available example sets:

- `water/` for a compact triatomic system that is ideal for distance and angle checks
- `ammonia/` for trigonal-pyramidal geometry and fragment/bond validation
- `methane/` for a simple tetrahedral reference

Each example folder contains:

- `.gjf` Gaussian input
- `.fchk` formatted checkpoint for openWFN
- `.xyz` legacy project-generated Cartesian companion
- a molecule-specific `README.md`

See [PROVENANCE.md](PROVENANCE.md) for checksums, calculation metadata,
relationships between files, redistribution terms, and the generation details
that were not recorded.

Quick manual checks from the repository root:

```bash
openwfn examples/water/water.fchk
openwfn examples/water/water.fchk summary
openwfn examples/water/water.fchk dist 2 1
openwfn examples/methane/methane.fchk graph
```
