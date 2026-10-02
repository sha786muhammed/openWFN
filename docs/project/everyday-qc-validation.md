# Staged QC validation and handoff

## Scope actually implemented

Baseline is 0.9.2 / 0991406. This branch implements roadmap units 1–5 plus
source-spin and MCP resource safeguards. It does **not** complete Phase 1 or
Phases 2–4. Scientific methods remain Experimental. No release version was
changed, no release was published and no phase gate was declared satisfied.

| Capability | Released 0.9.2 | This branch |
|---|---|---|
| Signed arbitrary MO cube, HOMO/LUMO, alpha/beta | Developer VTK preview only | Shared signed cube service and CLI/Python API |
| Named MO AO/atom/shell/angular projections | Absent | Mulliken or Löwdin, raw norm and overlap diagnostics |
| Mayer atom-pair bond orders | Absent | Total plus spin-density terms, charge/spin conservation |
| Orbital-energy DOS | Absent | Gaussian sigma/range/grid controls, alpha/beta, exports |
| PDOS | Absent | Atom/element/angular grouping, named weights and sum rule |
| Source restricted spin density in IOData | Discarded during combined occupation normalization | Retained from source alpha/beta occupations, including ROHF |
| Dense-analysis MCP AO bound | File-size containment only | Default 256-AO bound before overlap construction |
| Native Hirshfeld | Absent | Blocked; no unverified method exposed |
| Typed vibrations/IR/Raman/excited states/UV-Vis/NTO | Absent | Planned, not implemented |
| Analytic derivatives/QTAIM/ELF/LOL/NCI/basins | Absent | Planned, not implemented |

Registry methods are `orbital-composition`, `mayer`, `dos`, `pdos`.
CLI/Python allow documented parameters. Batch/report/MCP reuse the same
registered defaults; their custom parameter transport is future work.
Cube output remains outside read-only MCP. Model schema stays 2.0 and result
schema stays 1.0. Existing numerical kernels and safeguards were retained.

## Evidence, classified honestly

| Unit | Numerical evidence | Boundaries |
|---|---|---|
| MO cube | Normalized Gaussian signed field/norm, chunk equivalence; independent GBasis 0.1.0 Cartesian and pure d values at 3 points, 1e-12 tolerance; five-format water fields 1e-7 | Synthetic d-shell spin channel, not broad molecular/high-l external validation |
| Composition | Analytic two-AO metric, half/half bonding case, signed Mulliken vs positive Löwdin, partition closure, invalid norms/overlap; same contracted-basis Molden/MWFN equivalence 2e-7 | Fresh PySCF molecular comparisons below; Löwdin is representation dependent |
| Mayer | Analytic restricted bond 1.0, one-alpha bond 0.5; independent cclib 1.8.1 MBO contractions 1e-12; water matrix equivalence four formats 2e-7; charge/spin closure and corrupted spin regression | cclib comparisons share orbital and overlap input; no new Multiwfn/ORCA run |
| DOS | Closed-form Gaussian peak/line shape/unit area, channel counting, analytic truncated area, resource/error cases, CSV/SVG export | Independent expansion from fresh PySCF energies below; spectrum is orbital-energy broadening |
| PDOS | Six grouping/method combinations, pointwise projection closure, raw norm corruption, missing data, bounded outputs | Fresh molecular projection comparisons below; signed Mulliken weights and AO-basis sensitivity |
| All registered defaults | Numerical data match CLI, Python, batch, embedded HTML report manifest and in-process read-only MCP | MCP parameters use defaults; expensive export remains outside MCP |

Stage full-suite results: MO 620 passed/1 skipped; composition 626/1;
Mayer 634/1; DOS 647/1; PDOS 656/1; spin/MCP hardening 666/1.
Final review-fix run: **667 passed, 1 skipped** in 36.01 s after the documentation handoff. Ruff passed.
Tests were added before implementation and their initial failures observed.
Independent bounded review found one Important issue: unchecked Mayer spin
closure. Its reproducing test failed before the fix and passes afterwards.
No other Critical/Important findings were reported. This is a bounded code
review, not an independent scientific certification.

## Follow-up molecular reference validation

PR CI exposed four missing optional-dependency guards in the MO field tests.
A clean core-only installation reproduced all four failures; those cases now
skip only when IOData is absent. The dedicated interoperability job explicitly
runs both the cube and everyday cross-format tests with IOData installed.
The optional-interface job now includes registered-analysis parity and the
independent cclib Mayer comparisons. No numerical assertions were relaxed.

`scripts/validate_everyday_pyscf.py` freshly computes six bounded reference cases
using PySCF 2.12.1: RHF water/STO-3G, methane/STO-3G, ammonia/6-31G*,
benzene/STO-3G, UHF OH/6-31+G*, and Cartesian RHF water/6-31G*.
Each converged SCF wavefunction is exported by PySCF to Molden and independently
ingested by openWFN through IOData. The report records geometry, basis, spin,
SCF energy, source hash, dependency versions, observed errors and cube warnings.

Comparisons cover alpha HOMO/LUMO and UHF beta HOMO/LUMO fields against PySCF's
AO evaluator, actual cube serialization/layout, atom compositions using
PySCF Mulliken populations (SciPy symmetric square root for Löwdin), Mayer
matrices independently constructed by cclib from PySCF coefficients/overlap,
and DOS/atom PDOS from an independent Gaussian expansion. Pure-basis PDOS is
compared for both conventions; Cartesian PDOS is compared for Mulliken.
The molecular validation job runs these six comparisons in CI.

Cartesian AO normalization differs between PySCF and openWFN. Mulliken
populations, Mayer indices and physical fields can be compared after source
normalization; Löwdin partitions and overlap eigenvalues depend on the AO
representation and are explicitly **not compared** for that Cartesian case.
The report preserves the unasserted Löwdin difference with `compared: false`.
The coarse cube grid can yield `partial` norm diagnostics; reference field
agreement does not erase those warnings.

Tolerances are 2e-7 for fields, compositions and Mayer, 5e-6 for serialized cube
values (limited by text precision), and 2e-6 orbitals/eV for DOS/PDOS after
Molden energy rounding. `validation/everyday-qc/pyscf-report.json` is a captured
external-comparison report, distinct from the original observed snapshots.
These are same-wavefunction post-processing checks, not validation of HF
accuracy, all elements, high angular momentum, ECPs or correlated densities.
All five methods remain **Experimental**.

Follow-up verification: **673 passed, 1 skipped** in the full optional-dependency
environment; clean core-only CI configuration: **611 passed, 62 skipped,
1 docs test deselected**. Ruff, repository/documentation checks and strict
MkDocs pass; internal validation and all 25 interoperability formats pass.
The core-only optional skips are expected and are not scientific evidence.

Reproduce the external comparisons with:

```bash
python -m pip install -e '.[test,interop,outputs]' pyscf==2.12.1
python scripts/validate_everyday_pyscf.py --output-dir /tmp/openwfn-pyscf-validation
python -m pytest tests/validation/test_everyday_pyscf.py -q
```

Primary API references: [PySCF Molden export](https://pyscf.org/_modules/pyscf/tools/molden.html)
and [PySCF AO evaluation](https://pyscf.org/pyscf_api_docs/pyscf.gto.html).

`validation/everyday-qc/report.json` contains bounded water/methane/ammonia
snapshots with input hashes and dependency versions. They are observed values,
not independent reference targets. Full-grid DOS/PDOS arrays are omitted.
The element PDOS PNG was inspected for axes, colors, curve shape and readability;
a selected valence-energy range correctly retains a truncation warning.

## Reproduction

```bash
python -m pip install -e '.[test,interop,outputs,mcp,docs]' qc-gbasis==0.1.0
python -m pytest -q
python -m ruff check .
python scripts/run_validation.py
python scripts/run_interop_validation.py
python scripts/check_repository.py --root .
python scripts/check_docs.py --root .
python -m mkdocs build --strict
```

Optional dependency tests skip when their independently supplied packages are
absent. The single remaining skipped test checks the core-only missing-IOData contract;
it is inapplicable because IOData is installed in this verification environment.
Do not describe skipped tests as validation evidence.

## Hirshfeld gate: unresolved scientific inputs

A neutral free-atom reference database is not present in the repository. Its
source/method, spherical averaging, spin configuration, radial grid accuracy,
licensing and immutable hashes must be established before native stockholder
charges can be defensible. The ordinary definition is
`w_A(r)=rho_A^0(r)/sum_B rho_B^0(r)` and
`q_A=Z_A-integral w_A(r) rho(r) dr`. The definition alone does not determine
free-atom density data, an ECP core reconstruction convention, or a reliable
quadrature tolerance. Picking arbitrary hydrogenic profiles would change the
scientific method while producing plausible numbers, so no such shortcut was
implemented. ORCA's fitted free-atom densities and HORTON proatom databases are
method references, not an acquired/verified redistributable dataset here.

Next admissible unit: choose and validate a versioned reference provider,
restrict its advertised elements/core treatment, add convergence-controlled
atom-centered quadrature and trusted same-wavefunction reference charges.
No Hirshfeld command or unsupported placeholder is advertised as implemented.
Phase 2 is gated on Phase 1 stability as requested. NTO amplitude conventions,
Raman intensity conversion, QTAIM completeness and basin topology each need
their own design and independent validation before implementation claims.

## Release strategy

Keep 0.9.2 as the stable release. Review the staged commits as a draft PR.
A future 0.10.0a1 can expose these five methods as Experimental after review;
a stable 0.10.0 needs reviewed reference captures, broader restricted/unrestricted
molecules and completed Phase 1 gates. Use separate prerelease/PR units for
spectroscopy, transition interpretation and real-space methods. Basin integration
is a separate advanced project. No date is promised for the later scientific gates.

## Extended Experimental audit

The reference corpus now has 11 real cases committed under `examples/everyday-qc/`.
See [the complete Experimental coverage ledger](experimental-coverage.md) for
charged, triplet, intermolecular and real output-reader evidence, analytic ESP
convergence histories (including a retained ammonium failure), and safety fixes.
The earlier six-case capture above describes the initial stabilization milestone.
