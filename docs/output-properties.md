# Source-reported output properties

Read values printed in a supported Gaussian, ORCA or Q-Chem output file.
The included cclib reader extracts the available fields; it does not run a new
calculation. Extraction remains Experimental because coverage depends on the
program, version and job type.

```bash
python -m openwfn.cli --format json calculation.out properties
```

Python uses the same result envelope:

```python
from openwfn import read_output

result = read_output("calculation.out")
print(result.as_dict())
```

Fields include geometry, molecular charge/multiplicity, the last parsed SCF
energy, frontier orbitals, dipole and its origin, source-reported atomic charges,
program version, methods, basis name, and the parser's normal-termination flag.
Only fields actually parsed are returned. Missing values remain null or empty.
SCF energy is not relabelled as a correlated or thermal energy. Orbital indices
are 1-based. Normal termination does not establish optimization convergence.
Charge sums differing by more than 1e-4 e produce a warning; this is a
diagnostic threshold and not universal numerical validation.

Human-readable output abbreviates arrays longer than eight entries, including
coordinates and reported atomic charges. Scalar diagnostics and warnings remain
visible. Use `openwfn --verbose calculation.out properties` to print the full
arrays, or `--format json` for complete machine-readable results. Python and
CSV results are not abbreviated.

`Analysis Validation Status` describes the openWFN analysis, not the source
calculation's convergence. `Result Status` describes this extraction result;
`Source Job Termination` separately reports normal, not normal, or unknown.

The reader detects the source program from the file contents; omit
`--input-format`. It is separate from `load()` and does not add missing
wavefunction data to a loaded calculation.
It is not yet registered as a batch analysis.
Mulliken/Löwdin charges here are values reported by the source program, whereas
the existing population commands recompute values from a complete wavefunction.
Density, populations and ESP are not reconstructed from insufficient output.
Extraction remains Experimental. Selected ORCA 5.0.3, Q-Chem, and Gaussian outputs
were compared with source values. A Gaussian CASSCF example correctly retained
an unavailable SCF energy. These checks do not establish coverage for every
program version or job type. Input contents and complete parser metadata are not embedded in
the result. Provenance includes the input hash and local source path.
