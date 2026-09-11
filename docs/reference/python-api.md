# Python API reference

The stable import surface is declared by `openwfn.__all__`. Import from `openwfn` rather than internal modules when possible.

## Loading and models

### `load(path) -> OpenWFNCalculation`

Load a supported calculation file through the parser registry. The returned typed model contains molecular structure and optional basis, orbital, and density data.

### `OpenWFNCalculation`

Top-level calculation model used by the v0.7 analysis stack. Check optional fields before electronic analyses.

## FCHK parsing

- `read_fchk(path)` — read FCHK records.
- `parse_fchk_scalars(lines)` — extract scalar metadata.
- `parse_fchk_arrays(lines)` — extract atomic numbers and coordinates.
- `parse_fchk_density(lines)` — parse density matrices when present.
- `parse_fchk_basis(lines)` — parse basis data.
- `parse_fchk_mos(lines)` — parse molecular-orbital data.

These low-level functions are public for specialized workflows, but `load` is the recommended entry point.

## Geometry and topology

- `distance(a, b)` — Euclidean Cartesian distance.
- `angle(a, b, c)` — angle centered at `b`.
- `dihedral(a, b, c, d)` — signed torsion.
- `detect_bonds(atomic_numbers, coordinates)` — covalent-radius heuristic.
- `build_graph(...)` and `MolecularGraph` — connectivity and fragments.

Python indices follow ordinary zero-based sequence semantics.

## Basis, density, and orbitals

- `eval_s_type_gto(...)` — evaluate an s-type Gaussian basis function.
- `compute_density(...)` — evaluate density from compatible basis and matrix data.
- `evaluate_mo(...)` — evaluate a molecular orbital.
- `make_bounding_box_grid(...)` — build a molecular Cartesian grid.

These are numerical building blocks. Units and array shapes must match the function contract; add convergence checks to research code.

## Export functions

- `export_vtk(...)`
- `export_json(...)`
- `export_csv(...)`
- `export_molecule_viewer(...)`

Outputs can disclose the underlying molecular data. Apply the same access controls used for the source file.

## Compatibility

The public import surface is versioned, but scientific behavior can be clarified between releases. Pin an exact openWFN version for reproducible work and review the [release history](../project/release-history.md).

