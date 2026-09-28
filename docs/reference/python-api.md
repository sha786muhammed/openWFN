# Python API reference

The stable import surface is declared by `openwfn.__all__`. Import from `openwfn` rather than internal modules when possible.

## Public import inventory

| Name | Role |
|---|---|
| `read_fchk` | Read FCHK records |
| `parse_fchk_arrays` | Parse atomic arrays |
| `parse_fchk_scalars` | Parse scalar metadata |
| `parse_fchk_density` | Parse density matrices |
| `parse_fchk_basis` | Parse basis data |
| `parse_fchk_mos` | Parse molecular-orbital data |
| `distance` | Cartesian distance |
| `angle` | Three-point angle |
| `dihedral` | Signed torsion |
| `detect_bonds` | Covalent-radius bond heuristic |
| `MolecularGraph` | Molecular graph type |
| `build_graph` | Build connectivity and fragments |
| `eval_s_type_gto` | Evaluate an s-type Gaussian function |
| `compute_density` | Evaluate compatible density data |
| `evaluate_mo` | Evaluate a molecular orbital |
| `make_bounding_box_grid` | Build a Cartesian molecular grid |
| `export_vtk` | Write a VTK scalar grid |
| `export_json` | Write JSON properties |
| `export_csv` | Write a CSV point table |
| `export_molecule_viewer` | Write a standalone molecular viewer |
| `OpenWFNCalculation` | High-level calculation API |
| `MODEL_SCHEMA_VERSION` | Model schema identifier |
| `BoundaryConditions` | Boundary-condition record |
| `CalculationData` | Canonical calculation model |
| `Provenance` | Input provenance record |
| `RESULT_SCHEMA_VERSION` | Result schema identifier |
| `ResultRecord` | Versioned analysis result |
| `BATCH_SCHEMA_VERSION` | Batch manifest schema identifier |
| `available_analyses` | List registered analysis names |
| `discover_inputs` | Discover batch inputs |
| `run_analysis` | Run one registered analysis |
| `run_batch` | Run batch analyses |
| `load` | Load a high-level calculation |

## Loading and models

### `load(path) -> OpenWFNCalculation`

Load a supported calculation file through the parser registry. The returned typed model contains molecular structure and optional basis, orbital, and density data.

### `OpenWFNCalculation`

Top-level calculation model used by the current analysis stack. Check optional
fields before electronic analyses.

### Model schema

`MODEL_SCHEMA_VERSION` is `"2.0"`. `Molecule.boundary_conditions` defaults
to an immutable isolated-system record. Periodic construction is rejected in
v0.8 and is reserved for a later periodic implementation.

`Provenance` records the source path, SHA-256 checksum, parser name, source
format, parser version, warnings, and named transformations. These fields make
ingestion decisions traceable without changing scientific values. Existing
constructor forms covered by the compatibility tests remain supported.

## Registered named analyses

| Name | Result |
|---|---|
| `beta-frontier` | Beta-spin HOMO, LUMO, and gap |
| `frontier` | Alpha/default HOMO, LUMO, and gap |
| `lowdin` | Löwdin populations and charges |
| `mulliken` | Mulliken populations and charges |
| `summary` | Molecular and calculation summary |

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
