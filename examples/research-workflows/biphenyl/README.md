# Biphenyl: larger conjugated wavefunction example

This is a 22-atom C12H10 example generated with PySCF 2.14.0, RHF/STO-3G,
charge 0 and multiplicity 1. Its geometry was constructed from two regular
carbon rings joined by a 1.5-angstrom C-C bond. It was **not optimized**.
The procedure and geometry are project-authored and distributed under MIT.
The generated numerical data have no third-party molecular dataset source.

`reference.json` contains the exact geometry, dependency versions, source
checksum, reference values and numerical comparison errors. The SCF reference
must converge before any post-processing comparison is accepted.

The procedure compares overlap, point density, ESP, Mulliken/Löwdin populations,
HOMO/LUMO fields and compositions with PySCF-based references; Mayer bond orders
with cclib; and DOS/PDOS with a separate Gaussian-broadening expression.
Check the report for the exact scope and tolerances. These comparisons use the
same wavefunction; they do not validate HF/STO-3G as a chemical prediction.

```bash
openwfn examples/research-workflows/biphenyl/biphenyl.molden orbitals frontier --spin all
openwfn examples/research-workflows/biphenyl/biphenyl.molden orbitals composition --mo homo --method lowdin
openwfn examples/research-workflows/biphenyl/biphenyl.molden population mulliken
openwfn examples/research-workflows/biphenyl/biphenyl.molden population lowdin
openwfn examples/research-workflows/biphenyl/biphenyl.molden bondorder mayer
openwfn examples/research-workflows/biphenyl/biphenyl.molden open
```

This file does not contain vibrational or excited-state records. Missing IR,
Raman, UV-Vis or NTO data must not be inferred from its ground-state orbitals.
Use actual frequency or excitation outputs for those workflows.

Reproduce the reference outside this folder:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python -m scripts.validate_research_examples --output-dir /tmp/openwfn-biphenyl-reference
```

Molden text and orbital phases can differ between dependency versions. Compare
the reported numerical quantities using documented tolerances, not only bytes.
