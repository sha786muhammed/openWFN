# File formats

| Format | Input | Output | Notes |
|---|---:|---:|---|
| Gaussian FCHK | Yes | — | Complete quantitative wavefunction path |
| Gaussian CHK | Via `formchk` | — | Gaussian utility required |
| Gaussian cube | Grid inspection | Yes | Regular scalar fields; not a molecular-analysis input |
| Gaussian log/out | Metadata inspection | — | Route and energy metadata; not a wavefunction input |
| XYZ | Yes | Yes | One frame; coordinates plus optional trailing atom columns |
| PDB | Yes | Yes | Structure and available bonds; standard element inference |
| MOL/SDF | Yes | Yes | V2000 molecular structure |

Use `openwfn FILE doctor` to inspect the parsed input kind and available
capabilities. Quantitative orbital, density, population, ESP, report, and
structure analyses require a molecular calculation, normally an FCHK. Cube
files provide volumetric grids, while Gaussian log/out files provide metadata.
Structure-only files cannot contain basis functions, orbital coefficients,
density matrices, or orbital energies. Missing scientific data is reported as
unavailable rather than guessed.

Multi-frame XYZ and multi-record SDF inputs are not silently truncated to the
first structure. Split them into individual files before analysis. SDF input is
currently limited to V2000 records.
