# Validation status and evidence

openWFN separates implementation availability from scientific confidence.

- **Stable** — supported interface with tests for expected behavior.
- **Validated** — compared against defined numerical invariants or reference expectations for the named validation set.
- **Experimental** — available for investigation, but evidence is not broad enough for routine research claims.
- **Unsupported** — required data, method, or verification is absent.

## Internal regression and invariants

The provenance-backed numerical validation fixtures currently cover water,
methane, and ammonia for the legacy core validation runner. That suite evaluates
geometry and electron-density conservation among its regression metrics:

```bash
python scripts/run_validation.py
```

Passing those cases establishes regression evidence for those fixtures and
tolerances; it does not prove accuracy for every molecule, basis, charge state,
or spin state.

Focused regression fixtures also cover source-faithful ECP nuclear charges,
ghost centers, unrestricted and restricted-open-shell frontier behavior,
post-HF files using an SCF density, zero-spin density validation, population
conservation, and chunked density-grid equivalence. These are regression
safeguards, not independent third-party validation of every special case.

Population and density consistency checks are part of the result contract: when
a calculation produces usable values but fails a configured conservation or
convergence tolerance, openWFN returns a warning and `status="partial"` rather
than presenting inconsistent numbers as clean successes.

## Independent parser comparisons

The external registry compares openWFN with `qc-iodata==1.0.1` using identical
FCHK inputs, immutable source commits, SHA-256 checksums, and explicit
tolerances.

| Evidence | Active cases | Metrics | Status |
|---|---|---|---|
| Independent FCHK parsing | water, benzene, LiH, oxygen (pure and Cartesian), helium high-l | total energy and alpha frontier orbitals | 24 comparisons passing |
| Independent producer parser | acetylene from Psi4 | parser fields | qc-iodata 1.0.1 limitation: cannot parse one adjacent fixed-width exponent pair |

The parser comparison verifies extraction of the listed values. It does not
independently validate population or density algorithms. Reproduce the complete
external matrix with:

```bash
python scripts/run_external_benchmarks.py \
  --input-root "$OPENWFN_BENCHMARK_INPUTS" \
  --output-dir /tmp/openwfn-external
```

See the [registry procedure](https://github.com/sha786muhammed/openWFN/blob/main/validation/external/procedures/qc-iodata.md)
for source commits, selection conventions, and tolerances.

The 0.9 interoperability work also has three pinned externally supplied
unrestricted wavefunctions: H2 WFX, O2 WFN, and LiH-cation WFX. The external
runner checks alpha, beta, and spin density at five points against an
independent GBasis evaluator and checks electron counts on one specified grid
per channel. Those fixed-grid counts are regression checks, not convergence
evidence.

## Independent analysis comparisons

Multiwfn `3.8(dev)` (2024-10-24) independently agrees with openWFN for
restricted water, unrestricted LiH, and Psi4-produced acetylene on the named
frontier and population metrics.

| Case | Wavefunction | Compared metrics | Status |
|---|---|---|---|
| Water | Restricted | HOMO, LUMO, Mulliken charges, Löwdin charges | 4 passing |
| LiH | Unrestricted doublet | Alpha HOMO, alpha LUMO, Mulliken charges, Löwdin charges | 4 passing |
| Acetylene | Restricted, Psi4 producer | Total energy, HOMO, LUMO | 3 passing |

Those comparisons validate only the named metrics and fixtures.

## Native Hirshfeld validation — 0.11 development

Native ordinary Hirshfeld populations and charges are independently validated
for the named **H/C/N/O all-electron** scope on the 0.11 development branch.
The method uses a versioned neutral spherical pro-atom library,
`openwfn-hirshfeld-proatoms-v1`. Ordinary unrestricted cases use the total
molecular density; this is not a spin-Hirshfeld definition.

HORTON-PART 1.1.8 is used only in validation CI and is not an openWFN runtime
dependency. The exact openWFN pro-atom radial profiles are supplied to the
external implementation so the pro-atom convention is fixed, while the
molecular density evaluator, molecular grid and stockholder partition are
independently implemented. The recorded HORTON-PART comparison uses common
molecular-grid integration (`grid_type=3`).

The promotion gates were fixed before the final evidence run:

- maximum per-atom openWFN/HORTON-PART charge difference: **1.0e-3 e**;
- maximum per-atom standard-to-fine openWFN charge shift: **5.0e-4 e**.

All ten cases pass both gates: water, methane, ammonia, carbon dioxide, benzene,
ethanol, ammonium, triplet oxygen, diffuse UHF OH, and the water dimer. The
largest independent difference is about **1.27e-4 e** for ammonium. The largest
standard-to-fine shift is about **8.55e-5 e** for diffuse UHF OH. Open-shell O2
and OH and charged NH4+ are therefore represented in the documented scope.

Authoritative machine-readable evidence:

- `validation/hirshfeld/reference-report.json`
- `validation/hirshfeld/convergence-report.json`
- `tests/validation/test_hirshfeld_evidence.py`

The claim remains deliberately narrow. Elements outside H/C/N/O,
ECP/pseudopotential cases, ghost-center ambiguity, alternative pro-atom
conventions, spin-Hirshfeld variants and correlated/post-SCF density definitions
are not validated by this evidence.

## Everyday-QC scoped validation

Successful MO cubes, orbital composition, Mayer, DOS and PDOS have the scoped
0.10-series validation evidence documented in the
[everyday-QC validation record](../project/everyday-qc-validation.md).
Gaussian-integral point ESP is also validated for its independent PySCF and
analytic radial checks. Warnings and failed conditioning, conservation or
convergence diagnostics retain their own partial/Experimental status rather
than inheriting a method-level label.

The complete coverage audit retains real examples, convergence failures,
output-reader evidence and visualization boundaries. Software execution alone
does not promote a scientific method.

## Experimental spectroscopy and excited states

Vibrational spectroscopy and excited-state/UV–Vis workflows have dedicated regression evidence but remain **Experimental**. They are intentionally not promoted by the existence of parser/unit/UI tests alone.

Vibrational evidence is documented in `validation/vibrational-spectroscopy/README.md`. Excited-state evidence is documented in `validation/excited-states-uvvis/README.md` and currently covers project-owned Gaussian/ORCA/Q-Chem source-like fixtures, method/convention safety, analytic Gaussian broadening, energy-to-wavelength Jacobian behavior, resource limits, interface parity, report parity, and Workbench payload parity.

For excited states, representation support is broader than validation support. A method family being representable does not mean every implementation/version or method-specific amplitude transformation has independent reference evidence. Transition-density/NTO work therefore remains gated behind explicit convention support and separate validation.

## Experimental real-space topology

Analytic density derivatives are implemented and provide the field values used
by the first-party QTAIM topology analysis. QTAIM remains **Experimental**.
Critical-point discovery uses a deterministic, bounded seed set and bounded
Newton/trust-region search; optional bond paths use bounded density-gradient
ascent. Every QTAIM result reports that the search is not exhaustive.

The finite-system relation `N_NCP - N_BCP + N_RCP - N_CCP = 1` is retained as
a diagnostic. Failure is strong evidence of an incomplete or unresolved
critical-point set, while satisfying the relation is necessary but not proof
of completeness. Near-degenerate Hessians remain unclassified instead of being
forced into a QTAIM type.

Software regression tests cover critical-point classification, bounded search,
duplicate merging, topology diagnostics, resource limits and synthetic bond
paths. Independent molecular comparisons against established QTAIM reference
results are still required before any validation-status promotion. Basin
surfaces/integration, QTAIM atomic charges or energies, and delocalization
indices are not part of this implementation.

## Coverage still needed

For native Hirshfeld, future validation is required before supporting elements
outside H/C/N/O, ECP/pseudopotential systems, ghost-center conventions,
transition metals or correlated/post-SCF density definitions. Other analysis
families still need their own evidence for broader high-angular-momentum,
program/version and chemical-space coverage.

Typed spectroscopy, NTOs, analytic density derivatives and QTAIM are
implemented but remain separate scientific validation gates. ELF/LOL, NCI and
basin integration remain future implementation/validation work.

## Reproduce the software checks

```bash
python -m pytest
python -m ruff check .
python scripts/check_docs.py --root .
python -m mkdocs build --strict
```

The independent Hirshfeld evidence is reproduced by the pinned validation-only
stack in `.github/workflows/hirshfeld-validation.yml` running:

```bash
python scripts/validate_hirshfeld.py --external --output-dir hirshfeld-validation
```

Read [limitations](../limitations.md) before publication and cite the exact
version used.
