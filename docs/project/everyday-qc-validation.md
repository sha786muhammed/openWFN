# Everyday QC validation and evidence

This page describes the **current** validation state for openWFN 0.11.0. Historical development captures remain in the repository for provenance, but they do not override the current capability registry in `validation/manifest.json`.

## Current status

| Capability | Current status | Evidence and boundary |
|---|---|---|
| Orbital composition | Validated | Mulliken/Löwdin post-processing is compared against independent same-wavefunction references for the documented everyday-QC corpus. Conditioning or normalization failures remain partial or Experimental. |
| Mayer bond order | Validated | Compared with independent contractions for the documented RHF/UHF scope, with charge and spin conservation checks. |
| DOS | Validated | Gaussian broadening of orbital energies for the documented reference scope. It is not an excited-state spectrum. |
| PDOS | Validated | Atom/element/angular projections with explicit projection-sum diagnostics; representation-dependent conventions remain documented. |
| Native point ESP | Validated | Gaussian-integral electronic ESP is checked against independent PySCF Coulomb references at committed points and analytic high-angular-momentum tests. |
| MO cube fields | Conditional | Field values are compared against independent references; a generated cube remains partial when its requested coarse grid fails the normalization/conservation diagnostic. |
| Ordinary Hirshfeld population | Validated | Independently compared against HORTON-PART for the named H/C/N/O all-electron ten-case scope. Unsupported elements, ECP/pseudopotential ambiguity, and ghost-center ambiguity remain unsupported. |
| Native vibrational spectroscopy | Experimental | Gaussian harmonic frequency/IR/Raman-activity parsing, normal-mode vectors, deterministic Gaussian broadening and cross-interface parity are implemented. Current fixtures/regressions are not an independent external scientific validation corpus. Raman activity is not converted to experimental intensity. |
| Excited states and UV–Vis | Experimental | Gaussian/ORCA/Q-Chem source-state parsing, method/amplitude conventions, transition dipoles when reported, UV–Vis broadening, and energy-to-wavelength Jacobian handling are tested. Current evidence is not an independent cross-program scientific validation campaign. |
| Offline workbench interface | Stable interface | Tested in offline desktop Chromium. Individual displayed scientific fields retain their own success/partial/Validated/Experimental status; Workbench rendering does not promote an analysis beyond its scientific evidence. |
| Local read-only MCP interface | Stable interface | Common registered analyses are parity-tested against CLI/Python/report results within the documented containment limits. Spectroscopy and excited-state scalar parameters route through the same registry. |
| Source-output property readers | Experimental | Source-reported extraction remains dependent on program/file-version coverage and does not imply a complete wavefunction. |

The machine-readable status index is `validation/manifest.json`. It identifies current capability status, the resource benchmark contract, and historical captures that must not be interpreted as current validation labels.

## Independent reference evidence

`validation/everyday-qc/pyscf-report.json` is the main same-wavefunction external-comparison capture. PySCF 2.12.1 generates or reads the documented RHF/UHF wavefunctions; openWFN ingests them through the pinned interoperability layer. Comparisons cover orbital fields, compositions, Mayer matrices, DOS/PDOS and native Coulomb point ESP.

The references test **post-processing correctness for the same wavefunction**. They do not validate Hartree-Fock as a physical model, all elements, all basis sets, ECP reconstruction, correlated densities or every quantum-chemistry program/version.

The committed real-molecule corpus lives in `examples/everyday-qc/`. Starting with 0.10.1, the same corpus is also packaged under `openwfn.example_data` and installed by:

```bash
openwfn examples install installed-examples
```

The 11 Molden inputs are then available under `installed-examples/everyday-qc/`, allowing the built wheel and the package downloaded back from public PyPI to run the same bounded workflow matrix used by release CI.

### Hirshfeld evidence

The ordinary neutral-pro-atom Hirshfeld implementation is independently checked against HORTON-PART for water, methane, ammonia, carbon dioxide, benzene, ethanol, ammonium, triplet oxygen, diffuse UHF OH, and the water dimer. The committed evidence and convergence records live under `validation/hirshfeld/`.

The Validated label is restricted to the documented H/C/N/O all-electron scope and fixed acceptance tolerances. It does not imply support for arbitrary elements, ECP/pseudopotential inputs, or ghost-center ambiguity.

### Vibrational spectroscopy evidence

Vibrational spectroscopy deliberately remains Experimental. Its current evidence is recorded in `validation/vibrational-spectroscopy/README.md` and covers:

- typed Gaussian frequency-block parsing and source units;
- signed imaginary frequencies;
- analytic Gaussian broadening behavior;
- explicit missing IR/Raman/vector failure states;
- Python/MCP parity for the same parameters;
- CLI table/CSV/plot routing;
- HTML report numerical payload parity;
- Workbench numerical payload parity and vector-availability behavior.

These are implementation and regression checks. They do **not** compare a declared molecular/program/method corpus against an independent vibrational-analysis implementation with fixed tolerances. They therefore do not justify a Validated label.

### Excited-state and UV–Vis evidence

The current Experimental evidence is recorded in `validation/excited-states-uvvis/README.md` and covers:

- Gaussian, ORCA, and Q-Chem source-state parsing with multi-job isolation;
- oscillator strengths and transition dipoles when actually reported;
- method-family and amplitude-convention preservation;
- dark-state, missing-value, invalid-value, and resource-limit behavior;
- deterministic Gaussian energy broadening;
- the energy-to-wavelength Jacobian;
- CLI/Python/MCP/report/Workbench parity.

This is parser, numerical-post-processing, and interface evidence. It does not establish independent cross-program accuracy for every TDDFT, EOM, ADC, spin-flip, multireference, core-excited, local-correlation, or other source method family.

## Resource workflow evidence

The release resource benchmark runs ten prescribed CLI workflows for each of eleven real molecular inputs:

1. summary/geometry
2. Mayer bond order
3. DOS
4. PDOS
5. density cube
6. MO cube
7. offline workbench export
8. native point ESP
9. HTML report
10. ordinary Hirshfeld population

That is 110 commands in total. The benchmark checks command completion, timeout, observed process-tree RSS and generated-output size. **Resource/command success does not establish scientific validation.** Scientific status is evaluated separately by capability-specific reference tests and by each result's diagnostics.

The vibrational and excited-state features use different source-output classes and therefore do not silently expand this everyday-QC release benchmark. Their parser/API/CLI/report/Workbench tests are gated separately until provenance-complete independent validation corpora are established.

The benchmark accepts an explicit corpus directory so release verification can run against installed package data instead of silently falling back to repository fixtures:

```bash
python scripts/benchmark_resources.py \
  --examples-dir installed-examples/everyday-qc \
  --output resource-report.json
```

It rejects an incomplete corpus rather than treating an empty or partial input set as a successful benchmark.

## Historical captures

Two files are intentionally retained as historical evidence:

- `validation/everyday-qc/report.json` is an earlier water/methane/ammonia regression snapshot. Its recorded validation labels describe that historical capture and are not the current capability status.
- `validation/everyday-qc/esp-report.json` records the earlier grid-ESP convergence study, including the retained ammonium partial result. It is not the current status source for native Gaussian-integral point ESP.

These files remain useful for provenance and regression history. `validation/manifest.json` explicitly marks them as non-authoritative for current status.

## Reproduction

Full source-checkout validation can be reproduced with:

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

Release CI additionally builds the wheel, installs it into a clean environment, installs the packaged everyday-QC corpus, and runs the resource benchmark against those installed inputs. After publication, CI downloads the exact version from public PyPI with the required `interop` and `resources` extras and repeats the same installed-corpus benchmark.

## Remaining scientific boundaries

Vibrational spectroscopy and excited-state/UV–Vis analyses remain Experimental until independently generated reference data and predeclared acceptance tolerances support narrower promotion. Genuine transition-density NTOs, analytic density derivatives, QTAIM/ELF/LOL/NCI topology and basin integration each require their own method definition, reference data and validation gate.

Cartesian AO normalization can differ across programs. Physical fields and representation-invariant quantities are compared where appropriate; representation-dependent Löwdin quantities are not claimed equivalent when the AO normalization convention differs. ECPs, arbitrary diffuse tails, broad high-angular-momentum molecular coverage and correlated post-SCF densities retain their documented limitations.

## Historical development record

The 0.10 development cycle progressed through staged numerical checks, independent PySCF comparisons, workflow stabilization, browser fixes and resource hardening. Version 0.11.0 integrates the later Hirshfeld, vibrational-spectroscopy, and excited-state feature lines while retaining their capability-specific evidence boundaries. Current release status is defined by the versioned release notes, `validation/manifest.json`, current tests, and exact-release CI evidence.
