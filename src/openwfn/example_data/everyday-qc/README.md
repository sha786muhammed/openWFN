# Real everyday QC examples

These 11 Molden files contain actual converged single-point HF calculations,
generated with PySCF 2.12.1 and its Molden exporter. They are not synthetic
parser excerpts. Geometries are explicitly prescribed demonstrations, not
claims of optimized structures or benchmark HF chemistry accuracy.
Generated data are distributed under the openWFN project's MIT license.

| File stem | Calculation | Purpose |
|---|---|---|
| water | RHF/STO-3G | Small restricted reference |
| methane | RHF/STO-3G | Tetrahedral bonding |
| ammonia | RHF/6-31G* | Polarized pure spherical basis |
| benzene | RHF/STO-3G | Aromatic system and degenerate orbitals |
| oh_diffuse_uhf | UHF/6-31+G*, doublet | Separate alpha/beta and diffuse functions |
| water_cartesian | RHF/6-31G*, Cartesian | Cartesian d normalization/order |
| carbon_dioxide | RHF/6-31G* | Linear multiple bonds |
| water_dimer | RHF/6-31+G* | Intermolecular/diffuse example |
| ethanol | RHF/STO-3G | Larger asymmetric organic molecule |
| oxygen_triplet | UHF/6-31G*, triplet | Open-shell spin-density treatment |
| ammonium_cation | RHF/6-31G*, charge +1 | Charged electron-count convention |

Install the source checkout and optional parser:

```bash
python -m pip install -e '.[interop]'
openwfn examples/everyday-qc/oxygen_triplet.molden orbitals frontier --spin all
openwfn examples/everyday-qc/oh_diffuse_uhf.molden orbitals composition --mo homo --spin beta --method lowdin
openwfn examples/everyday-qc/benzene.molden bondorder mayer
openwfn examples/everyday-qc/ethanol.molden orbitals cube --mo homo --spacing .15 --padding 6 --output ethanol-homo.cube
openwfn examples/everyday-qc/water_dimer.molden orbitals pdos --group-by element --export water-dimer-pdos.svg
```

MO cube, orbital-composition, Mayer, DOS and PDOS results are **Validated** for
the documented eleven-molecule reference scope. Read status/warnings, including
cube/grid conservation warnings, before interpreting numbers; failed or partial
diagnostics retain their actual status. Mulliken populations can be negative;
Löwdin populations depend on AO representation. DOS is an orbital energy
spectrum, not a periodic band structure. Mayer values are indices, not an
automatic bond classification, particularly for intermolecular pairs.

The source SHA-256, charge, spin, coordinates, basis and converged SCF energy
for each file are in `validation/everyday-qc/pyscf-report.json`, together with
independent same-wavefunction comparisons and declared tolerances. Repository
tests verify the committed hashes. Regenerate into a separate directory:

```bash
python -m pip install -e '.[test,interop,outputs]' pyscf==2.12.1
python scripts/validate_everyday_pyscf.py --output-dir /tmp/openwfn-examples
python scripts/validate_experimental_esp.py --output /tmp/openwfn-esp.json
```

Compare scientific values within tolerances when regenerating; degeneracy,
global MO phases and numerical library details can change file bytes. The
committed files and their manifest are the immutable regression inputs.
See `docs/project/experimental-coverage.md` for all Experimental pathways,
the ESP convergence failure deliberately retained, and unsupported legacy MO
calls. These files are source-checkout examples, not bundled wheel assets.
