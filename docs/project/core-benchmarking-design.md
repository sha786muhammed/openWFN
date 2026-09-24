# Core Product Boundary and Independent Benchmarking

## Purpose

openWFN should earn trust through reproducible numerical evidence. The command-line
interface, Python API, structured outputs, scientific analyses, and validation tools
form the supported core. Presentation features must not imply stronger scientific
validation than the data behind them.

## Product boundary

The supported core consists of parsers, the typed calculation model, geometry and
wavefunction analyses, validation, batch execution, and machine-readable exports such
as JSON, CSV, structures, and cube files.

Static HTML and Markdown reports remain supported research artifacts because they make
results reviewable and portable. They must preserve provenance, units, warnings, and
validation status, and users should retain the corresponding machine-readable output.

The interactive offline workbench remains available for visualization, teaching, and
exploration, but is classified as **Experimental**. It is not a numerical reference,
must not be the only archived result, and should not be presented as part of the trusted
scientific core. Its embedded coarse grids are visualization data unless separately
converged and validated.

## Documentation and interface changes

- Keep the existing `workbench` command to avoid breaking users.
- Change workbench result records from `Stable` to `Experimental`.
- Remove workbench from primary installation and quick-start paths.
- Describe reports as supported presentation artifacts and the workbench as optional.
- Keep all scientific warnings visible in workbench output and documentation.
- Do not redesign the workbench during the scientific benchmarking milestone.

## Independent benchmark registry

Extend the validation registry without replacing its current internal regression
checks. Each independently benchmarked case records:

- input identity and SHA-256 checksum;
- source and redistribution status;
- generating program, method, basis, charge, and multiplicity when known;
- reference program name and exact version;
- reference extraction procedure or command transcript;
- expected values, units, tolerances, and comparison status;
- platform information and the openWFN version or commit tested.

Reference outputs may be stored only when their redistribution terms permit it.
Otherwise, store derived numerical expectations and a reproducible local extraction
procedure, without distributing third-party binaries or restricted input files.

## Initial benchmark matrix

The first external matrix covers complementary scientific cases:

| Case | Purpose | Required comparisons |
|---|---|---|
| Water | Small restricted baseline | energy, electron count, frontier orbitals, populations |
| Benzene | Larger closed-shell system | frontier orbitals, populations, density convergence |
| LiH | Unrestricted density channels | alpha, beta, spin, and total electron counts |
| Oxygen | Open-shell and pure/cartesian coverage | frontier orbitals, populations, spin quantities |
| Acetylene | Independent producer compatibility | metadata, geometry, energy, frontier orbitals |
| Helium high-angular-momentum case | Basis-function edge coverage | orbital ordering and frontier quantities |

Multiwfn is the preferred first reference because it analyzes the same wavefunction
file directly. IOData can independently verify parsed records. PySCF is useful for
new, provenance-complete calculations and analytic cross-checks, but recomputed values
are comparable only when the method, basis conventions, geometry, and numerical options
match exactly.

## Comparison rules

Tolerances are defined per metric and justified from printed precision and numerical
method. Parser-extracted scalars and orbital energies use tight absolute tolerances.
Population analyses use tolerances appropriate to the reference convention. Grid
integrals require both electron-count accuracy and convergence across at least two
successive refinements; one apparently accurate grid is not sufficient.

A benchmark is marked passed only when its checksum, provenance, reference version,
metric comparison, and tolerance are all present. Missing reference software or
incomplete provenance produces `pending` or `skipped`, never `passed`.

## Automation and reporting

The benchmark runner produces deterministic JSON and Markdown reports. Internal
regression validation remains suitable for continuous integration. Independently
generated reference values are checked in CI after review, while reference-program
execution may remain an explicit maintainer workflow when licensing or installation
prevents unattended CI execution.

The documentation validation matrix clearly separates:

- implementation and regression tests;
- internal invariants and conservation checks;
- independent external comparisons;
- pending or unsupported cases.

## Release gate

The stable `0.8.0` release requires:

1. the workbench to be consistently labeled Experimental;
2. all existing tests and internal validation checks to pass;
3. independently benchmarked restricted and unrestricted cases;
4. documented tolerances, provenance, and reproducible reference procedures;
5. no unexplained numerical mismatch in a capability advertised as Validated;
6. an updated public validation report and limitations page.

The alpha release remains the public evaluation build until these conditions are met.
