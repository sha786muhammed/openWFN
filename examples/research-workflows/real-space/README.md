# Real-space fields and a local bond critical point

This procedure generates hydrogen, ethylene and 22-atom biphenyl RHF/STO-3G
wavefunctions. It compares density, gradient, Hessian, Laplacian, positive-definite
kinetic-energy density, ELF, LOL and NCI/RDG with direct PySCF AO contractions.
SciPy independently solves for one stationary point near the central bond;
openWFN must find the same point, density and Hessian eigenvalues.

The geometries are constructed, not optimized. Matching the same wavefunction
checks post-processing, not chemical accuracy. One bond critical point does not
establish complete topology or QTAIM basin integration.

From the repository root, with validation dependencies installed:

```bash
python -m pip install pyscf==2.14.0
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python -m scripts.validate_research_realspace \
  --output-dir /tmp/openwfn-realspace-reference
```

Choose a new or empty output directory. The procedure saves three Molden files
and `reference.json`: geometry, method, basis, dependency versions, SHA-256,
reference arrays, error tolerances and full result records. Existing inputs are
not replaced. The recipe and generated molecular data are project-authored
under the repository's MIT license; PySCF is an external validation dependency.

Field comparisons use relative tolerance `2e-6` and absolute tolerance `2e-8`.
The bond-critical-point position tolerance is `2e-5 bohr`. On the checked
PySCF 2.14.0 run, the local bond-point densities were:

| Constructed molecule | Density (electron/bohr³) |
| --- | ---: |
| Hydrogen | 0.2563934581 |
| Ethylene | 0.3134139047 |
| Biphenyl | 0.2513480450 |

These are reference values for this recipe, not experimental observations.
Keep the generated report with your results. Experimental method labels are
unchanged; finite point comparisons do not validate an entire molecular field.

## Use your own wavefunction

```bash
openwfn examples/research-workflows/biphenyl/biphenyl.molden capabilities
openwfn examples/research-workflows/biphenyl/biphenyl.molden open
```

Select **All calculation methods and requirements**, then **Density fields and
localization** or **QTAIM topology**. Field points and search seeds are in bohr.
Choose a spin channel explicitly for open-shell ELF/LOL. The QTAIM workflow
lets you choose seeds, iteration limits and whether to trace bounded bond paths.
Save JSON for settings, masks, units, warnings and provenance.

Python uses the same methods:

```python
import json
from pathlib import Path
from openwfn import load
from openwfn.analysis.qtaim import QTAIMSettings

calc = load("examples/research-workflows/biphenyl/biphenyl.molden")
fields = calc.analyze("density-derivatives", points_bohr=[[0.21, 0.37, 0.29]])
topology = calc.analyze("qtaim", seeds_bohr=[[0.05, 0.03, 0.02]],
    settings=QTAIMSettings(max_iterations=96), include_bond_paths=False)
with Path("biphenyl-fields.json").open("x") as output:
    json.dump(fields.as_dict(), output, indent=2, allow_nan=False)
print(topology.status, topology.warnings)
```

The explicit seed probes one region only. A `partial` result must remain partial
in a report or assistant explanation, even when a selected point agrees with
the reference.
