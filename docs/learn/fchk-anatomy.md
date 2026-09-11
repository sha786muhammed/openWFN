# Anatomy of a formatted checkpoint file

Gaussian checkpoint (`.chk`) files are proprietary binary files. A formatted checkpoint (`.fchk`) is a text representation produced by Gaussian's `formchk` utility. openWFN reads `.fchk` directly; for `.chk`, it can call an installed `formchk` executable but does not decode the binary format itself.

## Record structure

An FCHK file begins with descriptive header lines and then labeled scalar or array records. A record identifies its data type and, for arrays, a count. Common groups include:

| Group | Examples | Used for |
|---|---|---|
| Molecular state | charge, multiplicity, electron counts | summary and spin interpretation |
| Structure | atomic numbers, Cartesian coordinates | geometry and topology |
| Basis | shell types, exponents, contraction coefficients | Gaussian basis evaluation |
| Orbitals | orbital energies and MO coefficients | frontier-orbital analysis |
| Density | total and spin density matrices | density, population, and ESP methods |
| Calculation metadata | total energy, method-dependent records | provenance and diagnostics |

Not every job writes every record. A geometry-only file may support distances but not density analysis. Restricted and unrestricted calculations can also expose different orbital and density records.

## Coordinates and units

FCHK Cartesian coordinates are stored in atomic units. openWFN converts molecular coordinates to ångströms at the parser boundary for structural operations and presentation. Grid controls for density and ESP use bohr, as stated in the CLI help and method pages.

## Conversion

```bash
openwfn calculation.chk formchk
openwfn calculation.chk formchk calculation.fchk
```

This requires Gaussian's `formchk` in `PATH`. If you do not have Gaussian utilities, request an `.fchk` file from the calculation author.

## Inspect before analysis

```bash
openwfn calculation.fchk info
openwfn --format json calculation.fchk doctor
```

Treat FCHK files as research data: they may encode unpublished structures and results. See [Security and data privacy](../project/security.md).
