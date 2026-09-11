# Offline workbench

```bash
openwfn water.fchk workbench water-workbench.html --open
```

The resulting HTML contains the molecule, provenance, analysis properties, volumetric fields, CSS, JavaScript, and vendored 3Dmol engine. It works through `file://` without a server or network request.

Workspaces include Structure, Orbitals, Density, ESP, and Measurements. Select two atoms for a distance, three for an angle, or four for a signed dihedral. Surface panels show isovalue, units, grid settings, phase legend, and validation state.

Do not use `--overwrite` unless replacing the destination is intentional.
