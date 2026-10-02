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

## Use from a source checkout

```bash
python -m pip install -e '.[interop]'
openwfn examples/everyday-qc/oxygen_triplet.molden orbitals frontier --spin all
openwfn examples/everyday-qc/oh_diffuse_uhf.molden orbitals composition --mo homo --spin beta --method lowdin
openwfn examples/everyday-qc/benzene.molden bondorder mayer
openwfn examples/everyday-qc/ethanol.molden orbitals cube --mo homo --spacing .15 --padding 6 --output ethanol-homo.cube
openwfn examples/everyday-qc/water_dimer.molden orbitals pdos --group-by element --export water-dimer-pdos.svg
```

## Use from the installed 0.10.1 package

The same versioned corpus is bundled with the wheel. Install it without cloning
the repository:

```bash
python -m pip install "openwfn[interop,resources]==0.10.1"
openwfn examples install installed-examples
openwfn installed-examples/everyday-qc/oxygen_triplet.molden orbitals frontier --spin all
```

The packaged Molden inputs are byte-identical copies of this source corpus. The
release resource benchmark uses these installed files when checking the built
wheel and again after downloading the exact release from public PyPI.

Orbital-composition, Mayer, DOS and PDOS results are **Validated** for the
documented eleven-molecule same-wavefunction reference scope. Native integral
point ESP also has independent reference evidence. MO field values are checked
against independent evaluators, while an individual cube remains partial when
its requested grid fails the normalization diagnostic. Read status and warnings
before interpreting numbers; failed or partial diagnostics retain their actual
status.

Mulliken populations can be negative; Löwdin populations depend on AO
representation. DOS is an orbital-energy spectrum, not periodic band structure
or an experimental excited-state spectrum. Mayer values are indices, not an
automatic bond classification, particularly for intermolecular pairs.

The source SHA-256, charge, spin, coordinates, basis, and converged SCF energy
for each file are recorded in `validation/everyday-qc/pyscf-report.json`,
together with independent same-wavefunction comparisons and declared
tolerances. `validation/manifest.json` is the authoritative current status
index. Repository tests verify the committed input hashes and the installed
package corpus.

Regenerate reference calculations into a separate directory:

```bash
python -m pip install -e '.[test,interop,outputs]' pyscf==2.12.1
python scripts/validate_everyday_pyscf.py --output-dir /tmp/openwfn-examples
python scripts/validate_experimental_esp.py --output /tmp/openwfn-esp.json
```

Compare scientific values within tolerances when regenerating; degeneracy,
global MO phases, and numerical-library details can change file bytes. The
committed files are immutable regression inputs. Historical captures remain in
the repository for provenance; current capability status is defined by the
canonical validation manifest and versioned release documentation.
