# Formats, units, and exports

## Inputs

| Format | Support | Notes |
|---|---|---|
| Gaussian `.fchk` | Direct | Primary analysis format |
| Gaussian `.chk` | Via `formchk` | Requires licensed Gaussian utility in `PATH` |

## Structure outputs

`convert` writes XYZ, PDB, MOL, or SDF. These formats primarily carry structure and connectivity; they do not preserve the full wavefunction. The legacy `xyz` command writes atom symbols and Cartesian coordinates.

```bash
openwfn molecule.fchk convert --to sdf --output molecule.sdf
openwfn molecule.fchk xyz molecule.xyz
```

## Scientific outputs

Table and record output can be rendered as terminal tables, plain text, JSON, or CSV. `export` writes frontier or population tables based on the destination extension. `plot frontier` writes a publication-oriented figure. `density cube` writes Gaussian cube volumetric data.

## HTML outputs

`report build`, `workbench`, and `view` can create self-contained HTML. “Self-contained” means no openWFN server is required; it does not mean the artifact is free of research data.

## Units

| Quantity | Presentation or control unit |
|---|---|
| Molecular coordinates and distances | ångström |
| Angles and dihedrals | degree |
| Orbital and total energies | atomic units unless labeled otherwise |
| Density-grid spacing and padding | bohr |
| Electrostatic potential | atomic units |

Always follow the label in machine-readable output and the installed version's help. See [scientific methods](../science/geometry-topology.md) for definitions.

