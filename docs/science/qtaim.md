# QTAIM critical-point search

This interface is Experimental. It searches the total electron density for
stationary points and can trace bounded bond paths from the returned bond
critical points. It is not a complete QTAIM basin-integration implementation.

The input needs an isolated molecular calculation, a supported basis and total
density. Check capabilities first:

```python
from openwfn import load

calculation = load("molecule.molden")
print(calculation.capabilities())
result = calculation.analyze("qtaim", include_bond_paths=False)
print(result.as_dict())
```

The result includes critical-point classifications, density/Hessian quantities,
search settings, seed/convergence counts, topology diagnostics and optional
bond-path records. Coordinates and paths use bohr. The returned `conventions`
field states indexing and labels; its atom indices are zero-based, unlike the
one-based CLI geometry commands.

## Read the diagnostics

The search has finite bounds, seed and iteration limits, and merge tolerances.
It is explicitly non-exhaustive and returns `partial`, with a warning that the
topology may be incomplete. A satisfied topology relation does not establish
that every physical critical point has been found. Unresolved bond paths retain
their warnings instead of being presented as successful connections.

The direct Python interface accepts explicit `seeds_bohr` and `QTAIMSettings`.
Record those settings and study their effect before interpreting the results.
The scalar-only assistant/MCP surface uses bounded defaults, and is limited to
32 centers; it does not accept arbitrary seed arrays or settings objects.

No basin electron populations, basin atomic charges or localization/delocalization
indices are supplied by this search. Do not infer them from critical-point
density values. Review the [validation status](validation-status.md) and keep
the complete result, including units and source provenance.
