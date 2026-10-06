# Experimental functionality: evidence and real examples

This is a coverage audit, not a blanket promotion to Validated. Eleven actual
converged PySCF single-point wavefunctions are committed in
[`examples/everyday-qc`](https://github.com/sha786muhammed/openWFN/tree/main/examples/everyday-qc/).
The corpus includes restricted, doublet/triplet unrestricted, charged, pure
spherical, Cartesian, diffuse, aromatic and intermolecular examples.
Generated geometries are demonstrations, not optimized reference structures.
Methods, coordinates, energies, source hashes, dependencies and acceptance
tolerances are retained with each case in the captured reference report.

## Every Experimental or conditional pathway

| Pathway | Evidence in this repository | Remaining boundary/status |
|---|---|---|
| MO cubes | Eleven fresh PySCF cases: signed HOMO/LUMO for alpha and available beta; field/order/normalization and serialized cube checks | Validated for the named set; no comprehensive high-l, ECP or correlated orbital validation |
| Orbital composition | PySCF Mulliken population routine and SciPy symmetric square root on the same wavefunctions; atom partition/metric diagnostics | Validated for the named set; Cartesian Löwdin intentionally excluded across differing AO normalizations |
| Mayer orders | cclib independently builds occupied densities and contracts its MBO matrices from PySCF wavefunctions | Validated for the named set; conventional HF index, not a validated correlated improved-Mayer implementation |
| DOS/PDOS | Independent Gaussian expansion from PySCF energies and projections; both population conventions for pure bases, Mulliken for Cartesian | Validated for the named set; all-element/high-l/ECP coverage absent; broadened orbital energies only |
| Native Hirshfeld | Ten-case H/C/N/O all-electron set; independent HORTON-PART 1.1.8 comparison plus standard-to-fine openWFN grid refinement | Validated for that named scope; unsupported elements, ECP/pseudopotential and ghost-center cases remain outside scope |
| Analytic density derivatives | Analytic AO-gradient/Hessian regressions, finite-difference consistency checks, resource-bounded real-space evaluation and real-wavefunction smoke coverage | Experimental; broader independent molecular/reference evidence remains required |
| Natural Transition Orbitals | Unit/integration tests for complete occupied-to-virtual transition matrices, convention/mapping safeguards and pinned reference-validation hooks | Experimental; incomplete or unsupported transition-amplitude conventions remain unavailable rather than guessed |
| QTAIM topology | Exact Hessian-signature classification, bounded synthetic stationary-point searches, duplicate/resource-limit tests, synthetic two-attractor bond paths, registry contract tests and a real-wavefunction smoke case | Experimental and explicitly non-exhaustive; independent established-QTAIM molecular comparison is still required; basin properties are out of scope |
| ELF/LOL localization | Kernel/spin/resource regressions plus required independent PySCF AO-derivative reconstruction for restricted water, Cartesian water, charged ammonium, diffuse UHF OH and triplet UHF oxygen | Experimental; evidence is same-wavefunction HF scope only; correlated density conventions, ECP/pseudopotential, complex-orbital, periodic and broad high-l/program coverage remain outside scope |
| NCI/RDG | Kernel/resource/cube regressions plus required independent PySCF density/gradient/full-Hessian reconstruction for restricted water, Cartesian water, charged ammonium, hydrogen-bonded water dimer and triplet UHF oxygen | Experimental; total-density same-wavefunction HF scope only; automatic labels/thresholds, correlated-density, ECP, complex-orbital, periodic and basin claims remain outside scope |
| Electronic/total grid ESP | Analytic PySCF `int1e_rinv` contraction for water, diffuse UHF OH and ammonium, with spacing histories and electron counts | Experimental; **ammonium fails the declared tested-grid tolerance**, retained as partial evidence |
| Density integration/cube when conservation fails | Existing density/conservation regressions plus ESP histories and real workbench coarse density grids | Remains partial/Experimental whenever its actual grid fails; passing other inputs must not override this |
| Mulliken/Löwdin population when incomplete/unreliable | Existing malformed/source-density/charge and overlap-condition regression tests | Remains partial/Experimental for inconsistent or ill-conditioned input; there is no valid golden population for deliberately invalid data |
| Frontier orbitals when data are incomplete | Existing restricted/unrestricted/missing-virtual occupation tests; genuine CASSCF log absence case for the output reader | Incomplete frontier results remain partial; unavailable orbital energies cannot be fabricated |
| HTML workbench | Real water and UHF OH payload tests check embedded HOMO cube against shared core, layout and retained partial density warnings; existing offline/HTML/measurement tests | Stable interface for the eleven-case offline Chromium set; field-level partial warnings retained; no universal GPU/device claim |
| Source-reported output properties | Pinned actual ORCA 4.2 MP2 water log: printed SCF energy, Mulliken charges and dipole magnitude; Gaussian09 CASSCF-only water log correctly leaves SCF energy absent | Experimental reader; two source jobs only, not all supported programs/properties |
| Hidden legacy `mo` preview | Audit confirms CLI explicitly unavailable; regression ensures exported legacy `evaluate_mo` no longer returns an invented zero field | **Unsupported**, use the normalized-core `orbitals cube` service |

Source `Experimental` occurrences are reviewed as capability-specific states, not
as a blanket project label. Conditional partial-result labels describe
insufficient input/numerics, not a method awaiting promotion. Native Hirshfeld
is no longer in the unimplemented category: its scoped validation evidence is
committed under `validation/hirshfeld/`. Spectroscopy, NTOs, analytic density
derivatives, QTAIM, ELF/LOL and NCI/RDG are implemented but retain their own
Experimental validation gates. Basin integration remains a separate future
scientific gate.

## ELF/LOL independent evidence

`tests/validation/test_localization_pyscf_reference.py` is a required CI gate,
not a self-comparison. It regenerates fresh PySCF SCF wavefunctions, exports
Molden input, loads that wavefunction through openWFN and independently
reconstructs density, density gradient and positive-definite KED from PySCF AO
derivatives and density matrices. The Becke-Edgecombe ELF and Schmider-Becke
LOL formulas are then evaluated in the reference test without calling the
openWFN localization kernels.

The named set covers restricted water, Cartesian-basis water, charged ammonium,
diffuse UHF OH and triplet UHF oxygen. Open-shell cases compare alpha and beta
channels separately. Fixed tolerances are applied to density, KED, the
homogeneous-electron-gas reference, ELF and LOL. Passing this gate is evidence
for those same-wavefunction HF cases; it is not a universal validation or a
reason to promote the public method beyond Experimental.

## NCI/RDG independent evidence

`tests/validation/test_nci_pyscf_reference.py` is also a required CI gate and is
not a self-comparison. Fresh PySCF 2.12.1 wavefunctions are exported and loaded
through openWFN for the implementation side. The reference side independently
contracts PySCF AO values, first derivatives and second derivatives with the
density matrices to obtain `rho`, `grad(rho)` and the full Cartesian density
Hessian, then independently derives ordered eigenvalues, `lambda2`, RDG and
`sign(lambda2)*rho`.

The named set covers restricted water/STO-3G, Cartesian water/6-31G*, charged
ammonium/6-31G*, a hydrogen-bonded water dimer/6-31G* and triplet UHF O2/6-31G*
using total alpha+beta density. Separate finite-difference checks at water and
intermolecular water-dimer points guard the AO derivative/Hessian component
mapping. Passing this gate is evidence for the named same-wavefunction HF cases,
not a universal method validation.

## Hirshfeld promotion evidence

The ordinary neutral-pro-atom Hirshfeld implementation uses the versioned
`openwfn-hirshfeld-proatoms-v1` H/C/N/O reference library. Its fixed independent
comparison gate is `1.0e-3 e` maximum per-atom charge difference against
HORTON-PART 1.1.8, and its fixed numerical-convergence gate is `5.0e-4 e`
maximum standard-to-fine openWFN charge shift. All ten named cases pass both.
The worst external difference is approximately `1.27e-4 e`; the worst grid
shift is approximately `8.55e-5 e`.

This is not universal Hirshfeld validation. It does not support or validate
other elements, ECP/pseudopotential cases, ghost-center ambiguity,
spin-Hirshfeld definitions, alternative pro-atom conventions or correlated
post-SCF densities.

## ESP findings and the actual acceptance criterion

`validation/everyday-qc/esp-report.json` retains every tested grid, including
large coarse errors. At two off-grid points, the fine-grid criterion is
absolute ESP error below 0.005 hartree/e **and** the existing density electron
conservation criterion. Padding is fixed at 4 bohr; this is a spacing study,
not independent padding convergence. Water uses 0.1-bohr final spacing; diffuse
OH required further refinement to 0.07 bohr while remaining under two million
points. Ammonium at 0.1 bohr fails: its result is deliberately recorded partial,
not hidden by widening tolerances. Near nuclei, different geometries, tighter
cores and diffuse tails still need convergence studies.

The shared public ESP service reports grid electron counts, expected count,
spacing/padding and conservation error. It returns partial with a warning if
that grid fails conservation. Passing charge conservation does **not** prove
local Coulomb-quadrature convergence.

## Reproduce and inspect

```bash
python -m pip install -e '.[test,interop,outputs,mcp,docs]' pyscf==2.12.1 qc-gbasis==0.1.0
python scripts/validate_everyday_pyscf.py --output-dir /tmp/openwfn-molecular-references
python scripts/validate_experimental_esp.py --output /tmp/openwfn-esp.json
python -m pytest tests/validation/test_real_example_corpus.py tests/validation/test_everyday_pyscf.py tests/validation/test_localization_pyscf_reference.py tests/validation/test_nci_pyscf_reference.py tests/validation/test_experimental_esp.py -q
python scripts/validate_output_references.py --download --input-dir /tmp/openwfn-real-logs --output /tmp/openwfn-output.json
```

For the independent Hirshfeld comparison, use the pinned validation-only
packages from `.github/workflows/hirshfeld-validation.yml` and run:

```bash
python scripts/validate_hirshfeld.py --external --output-dir /tmp/openwfn-hirshfeld
```

Output references are from immutable cclib-data commit
`127b2229d584d54fb84a74e383edb18a271fc283`, and both file checksums are enforced.
Captured numeric comparisons are in `validation/everyday-qc/output-report.json`.
The logs' redistribution license was not established, so the logs themselves
are not copied into openWFN; the opt-in runner downloads the exact public inputs.
Existing synthetic parser excerpts are **not** counted as real calculations.

These checks cover numerical post-processing of specified wavefunctions, not
the chemical accuracy of their chosen electronic-structure models. Labels
remain conservative, and failures and exclusions stay visible.

## Stabilization record

Successful MO cube, composition, Mayer, DOS and PDOS results report Validated
for their named set, retaining partial/Experimental for unmet diagnostics. The
default integral ESP resolves the charged-grid limitation without erasing the
historical grid evidence. The workbench interface is Stable for its browser-
validated scope; coarse density fields retain partial/Experimental warnings.
Native Hirshfeld adds an independent ten-case H/C/N/O validation record rather
than inheriting status from software tests alone. NTOs, analytic density
derivatives, QTAIM, ELF/LOL and NCI/RDG remain Experimental until their own
broader independent evidence gates justify any narrower promotion.
