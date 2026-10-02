# Experimental functionality: evidence and real examples

This is a coverage audit, not a blanket promotion to Validated. Eleven actual
converged PySCF single-point wavefunctions are committed in
[`examples/everyday-qc`](https://github.com/sha786muhammed/openWFN/tree/feat/everyday-qc-staged/examples/everyday-qc).
The corpus includes restricted, doublet/triplet unrestricted, charged, pure
spherical, Cartesian, diffuse, aromatic and intermolecular examples.
Generated geometries are demonstrations, not optimized reference structures.
Methods, coordinates, energies, source hashes, dependencies and acceptance
tolerances are retained with each case in the captured reference report.

## Every Experimental pathway

| Pathway | Evidence in this repository | Remaining boundary/status |
|---|---|---|
| MO cubes | Eleven fresh PySCF cases: signed HOMO/LUMO for alpha and available beta; field/order/normalization and serialized cube checks | Experimental; no comprehensive high-l, ECP or correlated orbital validation |
| Orbital composition | PySCF Mulliken population routine and SciPy symmetric square root on the same wavefunctions; atom partition/metric diagnostics | Experimental; Cartesian Löwdin intentionally excluded across differing AO normalizations |
| Mayer orders | cclib independently builds occupied densities and contracts its MBO matrices from PySCF wavefunctions | Experimental; conventional HF index, not a validated correlated improved-Mayer implementation |
| DOS/PDOS | Independent Gaussian expansion from PySCF energies and projections; both population conventions for pure bases, Mulliken for Cartesian | Experimental; all-element/high-l/ECP coverage absent; broadened orbital energies only |
| Electronic/total grid ESP | Analytic PySCF `int1e_rinv` contraction for water, diffuse UHF OH and ammonium, with spacing histories and electron counts | Experimental; **ammonium fails the declared tested-grid tolerance**, retained as partial evidence |
| Density integration/cube when conservation fails | Existing density/conservation regressions plus ESP histories and real workbench coarse density grids | Remains partial/Experimental whenever its actual grid fails; passing other inputs must not override this |
| Mulliken/Löwdin population when incomplete/unreliable | Existing malformed/source-density/charge and overlap-condition regression tests | Remains partial/Experimental for inconsistent or ill-conditioned input; there is no valid golden population for deliberately invalid data |
| Frontier orbitals when data are incomplete | Existing restricted/unrestricted/missing-virtual occupation tests; genuine CASSCF log absence case for the output reader | Incomplete frontier results remain partial; unavailable orbital energies cannot be fabricated |
| HTML workbench | Real water and UHF OH payload tests check embedded HOMO cube against shared core, layout and retained partial density warnings; existing offline/HTML/measurement tests | Experimental visualization; no new interactive browser certification or universal rendering claim |
| Source-reported output properties | Pinned actual ORCA 4.2 MP2 water log: printed SCF energy, Mulliken charges and dipole magnitude; Gaussian09 CASSCF-only water log correctly leaves SCF energy absent | Experimental reader; two source jobs only, not all supported programs/properties |
| Hidden legacy `mo` preview | Audit confirms CLI explicitly unavailable; regression ensures exported legacy `evaluate_mo` no longer returns an invented zero field | **Unsupported**, use the new normalized-core `orbitals cube` service |

Source `Experimental` occurrences were reviewed in services, spectral/orbital
services, output_properties, workbench, CLI and result types. The label's type
declaration is not itself a scientific feature. Conditional partial-result
labels describe insufficient input/numerics, not a method awaiting promotion.
Hirshfeld, spectroscopy, NTO, QTAIM and basin analyses are unimplemented;
they are not Experimental implementations that can be validated here.

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

The shared public ESP service now reports grid electron counts, expected count,
spacing/padding and conservation error. It returns partial with a warning if
that grid fails conservation. Passing charge conservation does **not** prove
local Coulomb-quadrature convergence. The new regression was observed failing
before the safeguard change and passing afterwards.

## Reproduce and inspect

```bash
python -m pip install -e '.[test,interop,outputs,mcp,docs]' pyscf==2.12.1 qc-gbasis==0.1.0
python scripts/validate_everyday_pyscf.py --output-dir /tmp/openwfn-molecular-references
python scripts/validate_experimental_esp.py --output /tmp/openwfn-esp.json
python -m pytest tests/validation/test_real_example_corpus.py tests/validation/test_everyday_pyscf.py tests/validation/test_experimental_esp.py -q
python scripts/validate_output_references.py --download --input-dir /tmp/openwfn-real-logs --output /tmp/openwfn-output.json
```

Output references are from immutable cclib-data commit
`127b2229d584d54fb84a74e383edb18a271fc283`, and both file checksums are enforced.
Captured numeric comparisons are in `validation/everyday-qc/output-report.json`.
The logs' redistribution license was not established, so the logs themselves
are not copied into openWFN; the opt-in runner downloads the exact public inputs.
Existing synthetic parser excerpts are **not** counted as real calculations.
Other parsed output fields in the report are observations, not independent
validation targets.

These checks cover numerical post-processing of specified wavefunctions, not
the chemical accuracy of their chosen electronic-structure models. Labels
remain conservative, and all failures and exclusions stay visible.

## Verification of this audit

Full suite: **704 passed, 1 skipped** (88.30 seconds). Ruff, repository and
documentation checks, strict MkDocs, internal validation and all 25 interop
formats pass. The molecular/ESP/corpus subset passed, including expected partial
ESP behavior. A bounded independent read-only review found no Critical/Important
issues. This review is not scientific certification. The single skip is the
core-only missing-IOData contract in an environment where IOData is installed.
