# Wavefunction analysis, from the beginning

A quantum-chemistry calculation can save geometry, basis functions, orbitals,
occupations and density matrices. **Wavefunction analysis** uses those data
to calculate properties you can inspect and compare.

openWFN reads supported wavefunction files, grids, structures and calculation
outputs. It analyses existing data; it does not run a new electronic-structure
calculation. Different file types can provide different properties.

## From a calculation to a result

1. **Calculation** — a quantum-chemistry program optimizes a structure or evaluates an electronic state.
2. **Save the data** — export a supported file from the calculation program.
3. **Parsing** — openWFN maps records into a typed calculation model.
4. **Analysis** — geometry, topology, orbitals, density, populations, or potential are computed.
5. **Evidence** — tables, cube files, and reports make results inspectable; the offline workbench adds optional visualization.

Every result depends on the input method, basis set, molecular state, and numerical settings. A precise output is not automatically a physically complete conclusion. Record the calculation provenance and interpret derived quantities within their stated [validation status](../science/validation-status.md).

## What is directly read and what is derived

Direct records include atomic numbers, Cartesian coordinates, charge, multiplicity, energies, basis information, orbital coefficients, and density matrices when present. Derived results include distances, bond heuristics, frontier-orbital gaps, numerical density integrals, atomic populations, and electrostatic potentials.

If a required record is missing, openWFN cannot infer it from a picture or
summary. Run `capabilities` to see what your file supports.

```bash
openwfn molecule.molden capabilities
openwfn molecule.molden summary
```

## Where to go next

- Choosing a file: [Formats and required data](../reference/formats-and-exports.md)
- Using Gaussian checkpoints: [Anatomy of an FCHK file](fchk-anatomy.md)
- Running an analysis: [Your first analysis](../start/first-analysis.md)
- Learning the equations: [Scientific methods](../science/geometry-topology.md)
- Preparing defensible output: [Reproducible research](reproducibility.md)
