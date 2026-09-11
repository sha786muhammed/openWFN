# Python workflows

The Python API is useful when an analysis must be composed with notebooks, testing, or custom data processing.

```python
from openwfn import load

calculation = load("molecule.fchk")
print(calculation.molecule.formula)
print(calculation.energy)
```

The typed `OpenWFNCalculation` model groups the molecule, basis, orbitals, and density matrices. Optional data remain optional: inspect fields before requesting analyses that require them.

## Geometry

```python
from openwfn import angle, distance

coordinates = calculation.molecule.coordinates
oh = distance(coordinates[0], coordinates[1])
hoh = angle(coordinates[1], coordinates[0], coordinates[2])
```

Python sequence indices are zero-based, unlike CLI atom numbers.

## Density and orbitals

The public package exports low-level evaluators including `compute_density`, `evaluate_mo`, and `make_bounding_box_grid`. These require compatible basis, coefficient, and density data. Prefer the typed model as the source and validate numerical settings before treating a grid result as converged.

For the complete export list and signatures, see [Python API reference](../reference/python-api.md). For runnable command-line equivalents, see [CLI workflows](cli-workflows.md).

