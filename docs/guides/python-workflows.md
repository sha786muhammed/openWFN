# Python workflows

The Python API is useful when an analysis must be composed with notebooks, testing, or custom data processing.

```python
from openwfn import load

calculation = load("molecule.fchk")
print(len(calculation.molecule.atoms))
print(calculation.molecule.charge)
print(calculation.molecule.metadata.energy_hartree)
```

The typed `OpenWFNCalculation` model groups the molecule, basis, orbitals, and density matrices. Optional data remain optional: inspect fields before requesting analyses that require them.

## Geometry

```python
oh = calculation.geometry_distance(1, 2)
hoh = calculation.geometry_angle(2, 1, 3)
print(oh.data["value"])
print(hoh.data["value"])
```

The high-level geometry methods use the same one-based atom numbers as the CLI.

## Density and orbitals

The public package exports low-level evaluators including `compute_density`, `evaluate_mo`, and `make_bounding_box_grid`. These require compatible basis, coefficient, and density data. Prefer the typed model as the source and validate numerical settings before treating a grid result as converged.

For the complete export list and signatures, see [Python API reference](../reference/python-api.md). For runnable command-line equivalents, see [CLI workflows](cli-workflows.md).
