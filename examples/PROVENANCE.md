# Example provenance

This file is the authoritative provenance record for the example corpus. The
files are project-owned fixtures distributed under the repository's MIT
License. They are small test and demonstration inputs, not independent
reference calculations.

The formatted checkpoint files contain a Gaussian route and calculation
metadata, but they do not identify the Gaussian release that wrote them. Git
history establishes when the files entered this repository; it does not prove
the original executable version or command line. Those fields therefore remain
explicitly unrecorded.

## Water

- Intended relationship: the GJF is the project input; the FCHK is its tracked
  optimized-wavefunction companion. The shared title, formula, and route support
  that relationship, but the exact execution chain was not preserved.
- File-derived calculation: RHF/3-21G optimization, charge 0, multiplicity 1.
- Gaussian version: not recorded.
- Exact Gaussian invocation: not recorded.
- XYZ relationship: project-generated companion whose coordinate numbers match
  the FCHK Cartesian array; exact openWFN version and export command are not
  recorded. Do not use the legacy XYZ file as a numerical validation reference.

| File | SHA-256 |
|---|---|
| `examples/water/water.gjf` | `8c1d0665554fca3c9f356468782f93088ef08037fdd2a950425ba65ba9cdcf82` |
| `examples/water/water.fchk` | `f3c6cb5e1f9f205e49b439339bb0833160f56be68f40e1c1097db3f30f52dcf2` |
| `examples/water/water.xyz` | `2030f7dc5220d4ec5c59e262eac9e6b24f8f721872d056ed7399acf356af6a5f` |

The packaged `src/openwfn/example_data/water.fchk` is byte-identical to the
repository FCHK and has the same checksum.

## Ammonia

- Intended relationship: the GJF is the project input; the FCHK is its tracked
  optimized-wavefunction companion. The shared title, formula, and route support
  that relationship, but the exact execution chain was not preserved.
- File-derived calculation: RHF/3-21G optimization, charge 0, multiplicity 1.
- Gaussian version: not recorded.
- Exact Gaussian invocation: not recorded.
- XYZ relationship: project-generated companion whose coordinate numbers match
  the FCHK Cartesian array; exact openWFN version and export command are not
  recorded. Do not use the legacy XYZ file as a numerical validation reference.

| File | SHA-256 |
|---|---|
| `examples/ammonia/ammonia.gjf` | `4fa7a39a56c06c4d5bce27614e1be428526336acf068d904c66f9c6e13f88f52` |
| `examples/ammonia/ammonia.fchk` | `cc6ef792b77b38b35a176bcb9856f10c178ad072fb5f56e8fa78d0f91c817d90` |
| `examples/ammonia/ammonia.xyz` | `10634319c1b97f2c8dbedb70afe2c4c5857799f461e82e55302e3a0e5b6d28d8` |

## Methane

- Intended relationship: the GJF is the project input; the FCHK is its tracked
  optimized-wavefunction companion. The shared title, formula, and route support
  that relationship, but the exact execution chain was not preserved.
- File-derived calculation: RHF/3-21G optimization, charge 0, multiplicity 1.
- Gaussian version: not recorded.
- Exact Gaussian invocation: not recorded.
- XYZ relationship: project-generated companion whose coordinate numbers match
  the FCHK Cartesian array; exact openWFN version and export command are not
  recorded. Do not use the legacy XYZ file as a numerical validation reference.

| File | SHA-256 |
|---|---|
| `examples/methane/methane.gjf` | `58a38b49ddd85f3d5672df3ce56c22c10a86ecb4df0bbcfeb9f01a059b807549` |
| `examples/methane/methane.fchk` | `1c37731946a48c3b64abd2a6c6594322f15fa1a4d5081144ef3a53bc7337b343` |
| `examples/methane/methane.xyz` | `940612e80e2395b795d1a94b3e12d2284aa2760d000cb414fcd73667bd701f5f` |

## Maintaining this record

When an example changes, update its checksum here and in any validation
manifest that uses it. New scientific fixtures must include their source,
generation software and version, exact procedure, method, basis, charge,
multiplicity, redistribution status, and reference values with units and
tolerances. Use `not recorded` for an unavailable historical fact rather than
inferring it.
