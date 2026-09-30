# openWFN interoperability format validation

Overall: **PASSED** (25/25 formats)

| Format | Status |
|---|---|
| `charmm` | PASSED |
| `chgcar` | PASSED |
| `cp2klog` | PASSED |
| `cube` | PASSED |
| `extxyz` | PASSED |
| `fchk` | PASSED |
| `fcidump` | PASSED |
| `gamess` | PASSED |
| `gaussianinput` | PASSED |
| `gaussianlog` | PASSED |
| `gromacs` | PASSED |
| `json_qcschema` | PASSED |
| `locpot` | PASSED |
| `mol2` | PASSED |
| `molden` | PASSED |
| `molekel` | PASSED |
| `mwfn` | PASSED |
| `orcalog` | PASSED |
| `pdb` | PASSED |
| `poscar` | PASSED |
| `qchemlog` | PASSED |
| `sdf` | PASSED |
| `wfn` | PASSED |
| `wfx` | PASSED |
| `xyz` | PASSED |

## Cross-format scientific equivalence

Status: **PASSED** (59/59 metrics)

| Format | Metric | Expected | Observed | Absolute error | Tolerance | Status |
|---|---|---|---|---:|---:|---|
| `fchk` | atomic_numbers | [8, 1, 1] | [8, 1, 1] | 0 | 0 | PASSED |
| `fchk` | coordinates_angstrom | [[0, 0, 0.1140487477], [0, 0.7804708052, -0.4561949903], [0, -0.7804708052, -0.4561949903]] | [[2.0765610629969862e-32, 8.926428534125518e-32, 0.11404874769861381], [-8.361943085079024e-31, 0.7804708051752508, -0.45619499026527804], [-9.558010743042007e-17, -0.7804708051752508, -0.45619499026527804]] | 3.47e-11 | 1e-06 | PASSED |
| `fchk` | electron_count | 10 | 10.0 | 0 | 1e-06 | PASSED |
| `fchk` | basis_functions | 13 | 13 | 0 | 0 | PASSED |
| `fchk` | alpha_energies_hartree | [-20.4271908, -1.32098683, -0.685590948, -0.52981661, -0.477228505, 0.261094828] | [-20.4271908, -1.32098683, -0.685590948, -0.52981661, -0.477228505, 0.261094828] | 0 | 1e-06 | PASSED |
| `fchk` | alpha_occupations | [2, 2, 2, 2, 2, 0] | [2.0, 2.0, 2.0, 2.0, 2.0, 0.0] | 0 | 1e-06 | PASSED |
| `fchk` | frontier_gap_hartree | 0.738323333 | 0.738323333 | 0 | 1e-06 | PASSED |
| `fchk` | mulliken_charges | [-0.73288863, 0.36644432, 0.36644432] | [-0.73288863, 0.36644432, 0.36644432] | 0 | 1e-06 | PASSED |
| `fchk` | density_integral_electrons | 10.02148372 | 10.02148372 | 0 | 0.0002 | PASSED |
| `molden` | atomic_numbers | [8, 1, 1] | [8, 1, 1] | 0 | 0 | PASSED |
| `molden` | coordinates_angstrom | [[0, 0, 0.1140487477], [0, 0.7804708052, -0.4561949903], [0, -0.7804708052, -0.4561949903]] | [[0.0, 0.0, 0.11404874769861381], [-0.0, 0.7804708051752508, -0.45619499026527804], [-9.578107517652001e-17, -0.7804708051752508, -0.45619499026527804]] | 3.47e-11 | 1e-06 | PASSED |
| `molden` | electron_count | 10 | 10.0 | 0 | 1e-06 | PASSED |
| `molden` | basis_functions | 13 | 13 | 0 | 0 | PASSED |
| `molden` | alpha_energies_hartree | [-20.4271908, -1.32098683, -0.685590948, -0.52981661, -0.477228505, 0.261094828] | [-20.4271908, -1.32098683, -0.685590948, -0.52981661, -0.477228505, 0.261094828] | 0 | 1e-06 | PASSED |
| `molden` | alpha_occupations | [2, 2, 2, 2, 2, 0] | [2.0, 2.0, 2.0, 2.0, 2.0, 0.0] | 0 | 1e-06 | PASSED |
| `molden` | frontier_gap_hartree | 0.738323333 | 0.738323333 | 0 | 1e-06 | PASSED |
| `molden` | mulliken_charges | [-0.73288863, 0.36644432, 0.36644432] | [-0.73288863, 0.36644432, 0.36644432] | 0 | 1e-06 | PASSED |
| `molden` | density_integral_electrons | 10.02148372 | 10.02148373 | 1e-08 | 0.0002 | PASSED |
| `wfn` | atomic_numbers | [8, 1, 1] | [8, 1, 1] | 0 | 0 | PASSED |
| `wfn` | coordinates_angstrom | [[0, 0, 0.1140487477], [0, 0.7804708052, -0.4561949903], [0, -0.7804708052, -0.4561949903]] | [[0.0, 0.0, 0.11404874875696823], [-0.0, 0.7804708051752508, -0.45619498973610084], [-0.0, -0.7804708051752508, -0.45619498973610084]] | 1.06e-09 | 1e-06 | PASSED |
| `wfn` | electron_count | 10 | 10.0 | 0 | 1e-06 | PASSED |
| `wfn` | basis_functions | 21 | 21 | 0 | 0 | PASSED |
| `wfn` | alpha_energies_hartree | [-20.4271908, -1.32098683, -0.685590948, -0.52981661, -0.477228505, 0.261094828] | [-20.427191, -1.320987, -0.685591, -0.529817, -0.477229, 0.261095] | 4.95e-07 | 1e-06 | PASSED |
| `wfn` | alpha_occupations | [2, 2, 2, 2, 2, 0] | [2.0, 2.0, 2.0, 2.0, 2.0, 0.0] | 0 | 1e-06 | PASSED |
| `wfn` | frontier_gap_hartree | 0.738323333 | 0.738324 | 6.67e-07 | 1e-06 | PASSED |
| `wfn` | mulliken_charges | [-0.73288863, 0.36644432, 0.36644432] | [-0.73288862, 0.36644432, 0.36644432] | 1e-08 | 1e-06 | PASSED |
| `wfn` | density_integral_electrons | 10.02148372 | 10.02148371 | 1e-08 | 0.0002 | PASSED |
| `wfx` | atomic_numbers | [8, 1, 1] | [8, 1, 1] | 0 | 0 | PASSED |
| `wfx` | coordinates_angstrom | [[0, 0, 0.1140487477], [0, 0.7804708052, -0.4561949903], [0, -0.7804708052, -0.4561949903]] | [[2.0765610629969862e-32, 8.926428534125518e-32, 0.11404874769861381], [-8.361943085079024e-31, 0.7804708051752508, -0.45619499026527804], [-9.558010743042007e-17, -0.7804708051752508, -0.45619499026527804]] | 3.47e-11 | 1e-06 | PASSED |
| `wfx` | electron_count | 10 | 10.0 | 0 | 1e-06 | PASSED |
| `wfx` | basis_functions | 21 | 21 | 0 | 0 | PASSED |
| `wfx` | alpha_energies_hartree | [-20.4271908, -1.32098683, -0.685590948, -0.52981661, -0.477228505, 0.261094828] | [-20.4271908, -1.32098683, -0.685590948, -0.52981661, -0.477228505, 0.261094828] | 0 | 1e-06 | PASSED |
| `wfx` | alpha_occupations | [2, 2, 2, 2, 2, 0] | [2.0, 2.0, 2.0, 2.0, 2.0, 0.0] | 0 | 1e-06 | PASSED |
| `wfx` | frontier_gap_hartree | 0.738323333 | 0.738323333 | 0 | 1e-06 | PASSED |
| `wfx` | mulliken_charges | [-0.73288863, 0.36644432, 0.36644432] | [-0.73288863, 0.36644432, 0.36644432] | 0 | 1e-06 | PASSED |
| `wfx` | density_integral_electrons | 10.02148372 | 10.02148373 | 1e-08 | 0.0002 | PASSED |
| `mwfn` | atomic_numbers | [8, 1, 1] | [8, 1, 1] | 0 | 0 | PASSED |
| `mwfn` | coordinates_angstrom | [[0, 0, 0.1140487477], [0, 0.7804708052, -0.4561949903], [0, -0.7804708052, -0.4561949903]] | [[0.0, 0.0, 0.11404874769903588], [-0.0, 0.7804708051755536, -0.4561949902651435], [-0.0, -0.7804708051755536, -0.4561949902651435]] | 3.49e-11 | 1e-06 | PASSED |
| `mwfn` | electron_count | 10 | 10.0 | 0 | 1e-06 | PASSED |
| `mwfn` | basis_functions | 13 | 13 | 0 | 0 | PASSED |
| `mwfn` | alpha_energies_hartree | [-20.4271908, -1.32098683, -0.685590948, -0.52981661, -0.477228505, 0.261094828] | [-20.4271908, -1.32098683, -0.685590948, -0.52981661, -0.477228505, 0.261094828] | 0 | 1e-06 | PASSED |
| `mwfn` | alpha_occupations | [2, 2, 2, 2, 2, 0] | [2.0, 2.0, 2.0, 2.0, 2.0, 0.0] | 0 | 1e-06 | PASSED |
| `mwfn` | frontier_gap_hartree | 0.738323333 | 0.738323333 | 0 | 1e-06 | PASSED |
| `mwfn` | mulliken_charges | [-0.73288863, 0.36644432, 0.36644432] | [-0.73288863, 0.36644432, 0.36644432] | 0 | 1e-06 | PASSED |
| `mwfn` | density_integral_electrons | 10.02148372 | 10.02148373 | 1e-08 | 0.0002 | PASSED |
| `orcalog` | atomic_numbers | [8, 1, 1] | [8, 1, 1] | 0 | 0 | PASSED |
| `orcalog` | coordinates_angstrom | [[0, 0, 0], [0, 0.756, 0.587], [0, -0.756, 0.587]] | [[0.0, 0.0, 0.0], [0.0, 0.7560000263682725, 0.5869998755800175], [0.0, -0.7560000263682725, 0.5869998755800175]] | 1.24e-07 | 1e-06 | PASSED |
| `orcalog` | energy_hartree | -74.96 | -74.96 | 0 | 1e-06 | PASSED |
| `qchemlog` | atomic_numbers | [8, 1, 1] | [8, 1, 1] | 0 | 0 | PASSED |
| `qchemlog` | coordinates_angstrom | [[0, 0, 0], [0, 0.756, 0.587], [0, -0.756, 0.587]] | [[0.0, 0.0, 0.0], [0.0, 0.7560000005371661, 0.5870000004170852], [0.0, -0.7560000005371661, 0.5870000004170852]] | 5.37e-10 | 1e-06 | PASSED |
| `qchemlog` | energy_hartree | -74.96 | -74.96 | 0 | 1e-06 | PASSED |
| `gamess` | atomic_numbers | [8, 1, 1] | [8, 1, 1] | 0 | 0 | PASSED |
| `gamess` | coordinates_angstrom | [[0, 0, 0], [0, 0.756, 0.587], [0, -0.756, 0.587]] | [[0.0, 0.0, 0.0], [0.0, 0.7560000005371661, 0.5870000004170852], [0.0, -0.7560000005371661, 0.5870000004170852]] | 5.37e-10 | 1e-06 | PASSED |
| `cp2klog` | atomic_numbers | [2] | [2] | 0 | 0 | PASSED |
| `cp2klog` | coordinates_angstrom | [[0, 0, 0]] | [[0.0, 0.0, 0.0]] | 0 | 1e-06 | PASSED |
| `cp2klog` | energy_hartree | -2.0 | -2.0 | 0 | 1e-06 | PASSED |
| `cp2klog` | basis_functions | 2 | 2 | 0 | 0 | PASSED |
| `cp2klog` | alpha_energies_hartree | [-0.5, 0.1] | [-0.5, 0.1] | 0 | 1e-06 | PASSED |
| `cp2klog` | alpha_occupations | [2, 0] | [2.0, 0.0] | 0 | 1e-06 | PASSED |
