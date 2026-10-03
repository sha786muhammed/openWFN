# Everyday QC validation and evidence

This page describes the current everyday-QC validation state. The latest public
stable release remains openWFN 0.10.1; native Hirshfeld below describes the
0.11 development branch until that release is published. Historical development
captures remain in the repository for provenance, but they do not override the
current capability registry in `validation/manifest.json`.

## Current status

| Capability | Current status | Evidence and boundary |
|---|---|---|
| Orbital composition | Validated | Mulliken/Löwdin post-processing is compared against independent same-wavefunction references for the documented everyday-QC corpus. Conditioning or normalization failures remain partial or Experimental. |
| Mayer bond order | Validated | Compared with independent contractions for the documented RHF/UHF scope, with charge and spin conservation checks. |
| DOS | Validated | Gaussian broadening of orbital energies for the documented reference scope. It is not an excited-state spectrum. |
| PDOS | Validated | Atom/element/angular projections with explicit projection-sum diagnostics; representation-dependent conventions remain documented. |
| Native point ESP | Validated | Gaussian-integral electronic ESP is checked against independent PySCF Coulomb references at committed points and analytic high-angular-momentum tests. |
| Native Hirshfeld | Validated on 0.11 development branch | Ordinary neutral-pro-atom populations/charges for H/C/N/O all-electron wavefunctions in the named ten-case set. External HORTON-PART agreement and openWFN grid refinement both pass fixed gates. Unsupported elements, ECPs and ghost-center ambiguity are outside scope. |
| MO cube fields | Conditional | Field values are compared against independent references; a generated cube remains partial when its requested coarse grid fails the normalization/conservation diagnostic. |
| Offline workbench interface | Stable interface | Tested in offline desktop Chromium for the documented corpus. Individual displayed scientific fields retain their own success/partial/Experimental status. |
| Local read-only MCP interface | Stable interface | Common registered analyses are parity-tested against CLI/Python/batch/report results within the documented containment limits. |
| Source-output property readers | Experimental | Source-reported extraction remains dependent on program/file-version coverage and does not imply a complete wavefunction. |

The machine-readable status index is `validation/manifest.json`. It identifies
current capability status, the resource benchmark contract, and historical
captures that must not be interpreted as current validation labels.

## Independent reference evidence

`validation/everyday-qc/pyscf-report.json` is the main same-wavefunction
external-comparison capture for the 0.10 everyday-QC methods. PySCF 2.12.1
generates or reads the documented RHF/UHF wavefunctions; openWFN ingests them
through the pinned interoperability layer. Comparisons cover orbital fields,
compositions, Mayer matrices, DOS/PDOS and native Coulomb point ESP.

The references test **post-processing correctness for the same wavefunction**.
They do not validate Hartree-Fock as a physical model, all elements, all basis
sets, ECP reconstruction, correlated densities or every quantum-chemistry
program/version.

### Native Hirshfeld evidence

The 0.11 development branch adds a separate independent validation gate for
ordinary neutral-pro-atom Hirshfeld populations and charges. The committed
reference library is `openwfn-hirshfeld-proatoms-v1`, containing reproducibly
generated spherical neutral H/C/N/O densities with per-file hashes and
normalization checks.

External comparison uses HORTON-PART 1.1.8 only in validation CI; it is **not**
a runtime dependency of openWFN. The same versioned pro-atom radial profiles are
supplied to HORTON-PART so the stockholder convention is held fixed, while the
molecular density evaluation, molecular grid and Hirshfeld partition/integration
are independently implemented. HORTON-PART uses its common molecular-grid mode
(`grid_type=3`) for the recorded comparison.

The fixed promotion gates are:

- maximum per-atom openWFN/HORTON-PART charge difference: `1.0e-3 e`;
- maximum per-atom openWFN standard-to-fine-grid charge shift: `5.0e-4 e`.

All ten named cases pass both gates: water, methane, ammonia, carbon dioxide,
benzene, ethanol, ammonium, triplet oxygen, diffuse UHF OH, and the water dimer.
The largest external difference is approximately `1.27e-4 e` (ammonium), and
the largest standard-to-fine-grid shift is approximately `8.55e-5 e` (diffuse
UHF OH). Triplet O2 and OH use the ordinary total-density definition; ammonium
provides the charged-system case. The authoritative values and input SHA-256
records are in `validation/hirshfeld/reference-report.json` and
`validation/hirshfeld/convergence-report.json`.

This validation is deliberately scoped. It does not validate elements outside
H/C/N/O, ECP/pseudopotential systems, ghost-center conventions, spin-Hirshfeld
variants, correlated/post-SCF density definitions, or arbitrary numerical grids.

## Versioned real-molecule corpus

The committed real-molecule corpus lives in `examples/everyday-qc/`. Starting
with 0.10.1, the same corpus is also packaged under `openwfn.example_data` and
installed by:

```bash
openwfn examples install installed-examples
```

The 11 Molden inputs are then available under
`installed-examples/everyday-qc/`, allowing the built wheel and the package
downloaded back from public PyPI to run the same bounded workflow matrix used by
release CI.

## Resource workflow evidence

The 0.11 development resource benchmark runs ten prescribed CLI workflows for
each of eleven real molecular inputs:

1. summary/geometry
2. Mayer bond order
3. native Hirshfeld population/charges
4. DOS
5. PDOS
6. density cube
7. MO cube
8. offline workbench export
9. native point ESP
10. HTML report

That is **110 commands in total**. The benchmark checks command completion,
timeout, observed process-tree RSS and generated-output size.
**Resource/command success does not establish scientific validation.**
Scientific status is evaluated separately by capability-specific reference
tests and by each result's diagnostics.

The benchmark accepts an explicit corpus directory so release verification can
run against installed package data instead of silently falling back to
repository fixtures:

```bash
python scripts/benchmark_resources.py \
  --examples-dir installed-examples/everyday-qc \
  --output resource-report.json
```

It rejects an incomplete corpus rather than treating an empty or partial input
set as a successful benchmark.

## Historical captures

Two files are intentionally retained as historical evidence:

- `validation/everyday-qc/report.json` is an earlier water/methane/ammonia
  regression snapshot. Its recorded validation labels describe that historical
  capture and are not the current capability status.
- `validation/everyday-qc/esp-report.json` records the earlier grid-ESP
  convergence study, including the retained ammonium partial result. It is not
  the current status source for native Gaussian-integral point ESP.

These files remain useful for provenance and regression history.
`validation/manifest.json` explicitly marks them as non-authoritative for
current status.

## Reproduction

Full source-checkout reference validation can be reproduced with:

```bash
python -m pip install -e '.[test,interop,outputs,mcp,docs,resources]' pyscf==2.12.1 qc-gbasis==0.1.0
python -m pytest -q
python -m ruff check src tests scripts
python scripts/run_validation.py
python scripts/run_interop_validation.py
python scripts/check_repository.py --root .
python scripts/check_docs.py --root .
python -m mkdocs build --strict
python scripts/benchmark_resources.py --output resource-report.json
```

The independent Hirshfeld comparison additionally uses the validation-only
stack pinned in `.github/workflows/hirshfeld-validation.yml` and is reproduced
with `scripts/validate_hirshfeld.py --external`.

Release CI additionally builds the wheel, installs it into a clean environment,
installs the packaged everyday-QC corpus, and runs the resource benchmark
against those installed inputs. Public-PyPI verification applies only after an
actual release is published.

## Remaining scientific boundaries

Typed vibrational/IR/Raman workflows, excited-state/UV-Vis analysis, genuine
transition-data NTOs, analytic density derivatives, QTAIM/ELF/LOL/NCI topology
and basin integration remain future gated work. Hirshfeld still requires new
reference-density and validation work before adding elements beyond H/C/N/O or
supporting ECP/pseudopotential and ghost-center cases.

Cartesian AO normalization can differ across programs. Physical fields and
representation-invariant quantities are compared where appropriate;
representation-dependent Löwdin quantities are not claimed equivalent when the
AO normalization convention differs. ECPs, arbitrary diffuse tails, broad
high-angular-momentum molecular coverage and correlated post-SCF densities
retain their documented limitations.

## Historical development record

The 0.10 development cycle progressed through staged numerical checks,
independent PySCF comparisons, workflow stabilization, browser fixes and
resource hardening before the stable release. Those milestone descriptions are
historical context only. Current status is defined by
`validation/manifest.json`, committed capability-specific evidence, current
tests and the exact release CI evidence.
