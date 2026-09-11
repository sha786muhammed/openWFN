# Wavefunction analysis, from the beginning

A quantum-chemistry calculation produces more than a final energy. Its checkpoint data describe the molecular geometry, basis functions, molecular orbitals, occupation, and density matrices used to represent an electronic state. **Wavefunction analysis** turns those records into quantities a scientist can inspect, compare, and report.

openWFN focuses on Gaussian formatted-checkpoint (`.fchk`) data. It does not run an electronic-structure calculation and it does not replace Gaussian. It reads the result of a calculation and applies transparent post-processing methods.

## The analysis chain

1. **Calculation** — a quantum-chemistry program optimizes a structure or evaluates an electronic state.
2. **Serialization** — Gaussian's `formchk` utility converts its binary checkpoint into documented text records.
3. **Parsing** — openWFN maps records into a typed calculation model.
4. **Analysis** — geometry, topology, orbitals, density, populations, or potential are computed.
5. **Evidence** — tables, cube files, reports, and the offline workbench make results inspectable.

Every result depends on the input method, basis set, molecular state, and numerical settings. A precise output is not automatically a physically complete conclusion. Record the calculation provenance and interpret derived quantities within their stated [validation status](../science/validation-status.md).

## What is directly read and what is derived

Direct records include atomic numbers, Cartesian coordinates, charge, multiplicity, energies, basis information, orbital coefficients, and density matrices when present. Derived results include distances, bond heuristics, frontier-orbital gaps, numerical density integrals, atomic populations, and electrostatic potentials.

This distinction matters: a missing record cannot be reconstructed reliably from presentation data alone. Use `doctor` before a workflow to see which capabilities the file supports.

```bash
openwfn molecule.fchk doctor
openwfn molecule.fchk summary
```

## Where to go next

- New to checkpoint files: [Anatomy of an FCHK file](fchk-anatomy.md)
- Running an analysis: [Your first analysis](../start/first-analysis.md)
- Learning the equations: [Scientific methods](../science/geometry-topology.md)
- Preparing defensible output: [Reproducible research](reproducibility.md)

