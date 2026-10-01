# Source-reported output properties

This Experimental interface in 0.9.1 reads properties printed in QC text
output through the optional cclib reader. Install:

```bash
python -m pip install "openwfn[outputs]==0.9.1"
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

This pathway uses cclib content detection; omit `--input-format`. It is separate
from `load()` and does not add wavefunction capabilities to that object's model.
It is not yet registered as a batch analysis.
Mulliken/Löwdin charges here are values reported by the source program, whereas
the existing population commands recompute values from a complete wavefunction.
Density, populations and ESP are not reconstructed from insufficient output.
The preview is Experimental. Selected ORCA 5.0.3, Q-Chem, and Gaussian outputs
were compared with source values. A Gaussian CASSCF example correctly retained
an unavailable SCF energy. These checks do not establish coverage for every
program version or job type. Input contents and complete parser metadata are not embedded in
the result. Provenance includes the input hash and local source path.
