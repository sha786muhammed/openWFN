# File formats

| Format | Input | Output | Notes |
|---|---:|---:|---|
| Gaussian FCHK | Yes | — | Complete v0.7 wavefunction path |
| Gaussian CHK | Via `formchk` | — | Gaussian utility required |
| Gaussian cube | Yes | Yes | Regular scalar fields |
| Gaussian log/out | Metadata | — | Geometry and calculation metadata |
| XYZ | Yes | Yes | Coordinates only |
| PDB | Yes | Yes | Structure and available bonds |
| MOL/SDF | Yes | Yes | V2000 molecular structure |

XYZ cannot contain basis functions, orbital coefficients, density matrices, or orbital energies. Missing scientific data is reported as unavailable rather than guessed.
