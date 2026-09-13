# Python API reference

The stable import surface is declared by `openwfn.__all__`. Import from `openwfn` rather than internal modules when possible.

## Loading and models

### `load(path) -> OpenWFNCalculation`

Load a supported calculation file through the parser registry. The returned typed model contains molecular structure and optional basis, orbital, and density data.

### `OpenWFNCalculation`

Top-level calculation model used by the v0.7 analysis stack. Check optional fields before electronic analyses.

### Model schema v2 foundation

`MODEL_SCHEMA_VERSION` is `"2.0"`. `Molecule.boundary_conditions` defaults
to an immutable isolated-system record. Periodic construction is rejected in
v0.8 and is reserved for a later periodic implementation.

`Provenance` records the source path, SHA-256 checksum, parser name, source
format, parser version, warnings, and named transformations. These fields make
ingestion decisions traceable without changing scientific values. The v0.8
fields are additive, and existing v0.7 constructor forms remain supported.

## Named analyses and results

Use `available_analyses()` to discover stable registry names. Run an analysis
with `calculation.analyze(name)` after `load(path)`, or use
`run_analysis(calculation_data, name)` when working directly with the canonical
model.

Every registered analysis returns a `ResultRecord` using result schema
`RESULT_SCHEMA_VERSION`, currently `"1.0"`. Its JSON representation includes
the analysis name and version, scientific data and units, validation status,
input provenance, warnings, elapsed time, execution status, and structured
failure details. Existing `ResultRecord(kind, data, units, validation_status)`
construction remains supported.

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
