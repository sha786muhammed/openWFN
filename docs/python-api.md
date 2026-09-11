# Python API

```python
from openwfn.api import load

calculation = load("water.fchk")
distance = calculation.geometry_distance(1, 2)
print(distance.data["value"], distance.units["value"])

frontier = calculation.orbitals()
mulliken = calculation.population("mulliken")
density = calculation.density(spacing_bohr=0.25, padding_bohr=5.0)
```

The API returns typed calculation objects and `ResultRecord` values rather than parsing terminal output. Atom indices for geometry methods follow the command-line convention.

The stable calculation object exposes geometry distances, angles, and dihedrals;
frontier orbitals; Mulliken and Löwdin populations; and density integration.
These methods return `ResultRecord` objects with values, units, and validation
status. Parsers, models, analysis functions, and exporters remain available as
focused modules, while `openwfn.api.load` is the documented compatibility boundary.
