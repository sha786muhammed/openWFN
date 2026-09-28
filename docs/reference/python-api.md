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

| Method | Contract |
|---|---|
| `analyze(name)` | Preferred reproducible route for a registered named analysis |
| `analyze_geometry()` | Basic atom count, charge, and multiplicity |
| `geometry_distance(i, j)` | Distance in ångströms; one-based atom numbers |
| `geometry_angle(i, j, k)` | Angle in degrees; one-based atom numbers |
| `geometry_dihedral(i, j, k, l)` | Signed torsion in degrees; one-based atom numbers |
| `orbitals(spin)` | Frontier orbitals for `"alpha"`, `"beta"`, or spin-complete `"all"` |
| `population(method)` | Populations for `"mulliken"` or `"lowdin"` |
| `density(kind, spacing_bohr=0.15, padding_bohr=6.0)` | Grid integration for `"total"`, `"alpha"`, `"beta"`, or `"spin"` |

All these methods return `ResultRecord`. Specialized methods are convenience
interfaces; use `analyze(name)` when analysis identity, registry version, and
elapsed time are important to an automated workflow. Every high-level result
includes available source provenance and parser warnings. Unsupported option
values raise `ValueError`; requests requiring records absent from the input
raise `DataUnavailableError`.

### Model schema

`MODEL_SCHEMA_VERSION` is `"2.0"`. `Molecule.boundary_conditions` defaults
to an immutable isolated-system record. Periodic construction is rejected in
v0.8 and is reserved for a later periodic implementation.

`Provenance` records the source path, SHA-256 checksum, parser name, source
format, parser version, warnings, and named transformations. These fields make
ingestion decisions traceable without changing scientific values. Existing
constructor forms covered by the compatibility tests remain supported.

## Scientific result safeguards

For Gaussian formatted-checkpoint inputs, openWFN preserves source electronic metadata instead of reconstructing it when the file provides the authoritative record. FCHK `Nuclear charges` supplies effective nuclear charges for ECP and ghost centers. FCHK `Number of electrons` is the preferred total-electron expectation for density conservation; alpha and beta electron records are used for spin-resolved expectations. If a required source value is absent, the deterministic fallback is recorded in result warnings.

Mulliken and Löwdin population results carry a conservation error. A scientifically inconsistent but still numerically usable result is retained with `status="partial"` and a warning instead of being labeled as a clean success. Density integration and cube export use the same principle: validation status is assigned from the actual generated grid and its electron-conservation check.

For post-HF calculations, openWFN does not claim correlated-density support unless a supported post-SCF density is actually parsed and selected. If the available matrix is the SCF density, the result names `density_source="scf"` and emits a warning that the SCF density was used.

For unrestricted calculations, select `spin="all"`; `calculation.orbitals(spin="all")` returns both channels plus the true overall HOMO. The corresponding registered analysis is `frontier-all`. The default alpha-only view remains available for backward compatibility but warns when a beta channel exists.

The default density-grid spacing is **0.15 bohr** with 6.0 bohr padding. These defaults are an accuracy/performance starting point, not a convergence guarantee. Density grids are evaluated in bounded chunks to reduce peak AO-matrix memory, but researchers should still converge spacing and padding for the molecule and property being reported.

## Registered named analyses

| Name | Result |
|---|---|
| `beta-frontier` | Beta-spin HOMO, LUMO, and gap |
| `frontier` | Alpha/default HOMO, LUMO, and gap |
| `frontier-all` | Alpha and beta frontiers plus the true overall HOMO for unrestricted calculations |
| `lowdin` | Löwdin populations and charges |
| `mulliken` | Mulliken populations and charges |
| `summary` | Molecular and calculation summary |

Use `available_analyses()` to discover registered names. Run an analysis
with `calculation.analyze(name)` after `load(path)`, or use
`run_analysis(calculation_data, name)` when working directly with the canonical
model.

Every registered analysis returns a `ResultRecord` using result schema
`RESULT_SCHEMA_VERSION`, currently `"1.0"`. Its JSON representation includes
the analysis name and version, scientific data and units, validation status,
input provenance, warnings, elapsed time, execution status, and structured
failure details. Existing `ResultRecord(kind, data, units, validation_status)`
construction remains supported.

## Batch API

`run_batch(...)` accepts the existing `inputs`, `operation`, `workers`, and `output_dir` arguments plus optional named analyses, resume/discovery controls, and `frontier_spin="alpha"|"beta"|"all"`. The `frontier_spin` selector applies when `frontier` is requested: alpha preserves the historical analysis, beta maps it to `beta-frontier`, and all maps it to the spin-complete `frontier-all` analysis. The spin selection participates in the configuration fingerprint so resume does not reuse incompatible frontier results.

Batch records preserve usable `partial` analyses and their warnings/data. A record becomes `error` only when every requested analysis failed.

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

These public geometry and topology functions use one-based atom numbers,
matching the CLI and `OpenWFNCalculation` geometry methods. Internal model
fields and Python arrays retain normal zero-based indexing: examples include
`molecule.atoms`, `BasisShell.atom_index`, `Bond.atom1`/`Bond.atom2`, and
orbital coefficient arrays. Each public method documents which convention it
accepts; do not assume one convention applies to every integer field.

Summary bond and fragment counts are inferred with the covalent-radius heuristic, not read as authoritative connectivity from FCHK. Ghost centers are excluded from physical formula, center-of-mass, bond, and fragment summaries while remaining represented as calculation centers.

## Basis, density, and orbitals

- `eval_s_type_gto(...)` — evaluate an s-type Gaussian basis function.
- `compute_density(...)` — evaluate density from compatible basis and matrix data.
- `evaluate_mo(...)` — evaluate a molecular orbital.
- `make_bounding_box_grid(...)` — build a molecular Cartesian grid.

These are numerical building blocks. Units and array shapes must match the
function contract, and non-finite scientific values are rejected by the public
models and result envelope. Add convergence checks to research code.

## Export functions

- `export_vtk(...)`
- `export_json(...)`
- `export_csv(...)`
- `export_molecule_viewer(...)`

Outputs can disclose the underlying molecular data. Apply the same access controls used for the source file.

## Compatibility

The public import surface is versioned, but scientific behavior can be clarified between releases. Pin an exact openWFN version for reproducible work and review the [release history](../project/release-history.md).
