# Excited states and UV–Vis validation record

Status: **Experimental**.

This record documents the evidence currently present for the method-general excited-state and UV–Vis feature. It does not promote the feature to Validated.

## Implemented evidence

### Source parsing

Project-owned source-like fixtures cover:

- Gaussian TDDFT/CIS excited states, oscillator strengths, transition contributions, transition dipoles, dark states, Link1 separation, malformed/non-finite data, and state-count limits;
- ORCA modern absorption tables, state-only/EOM-style output, SA-CASSCF transitions, unknown-method fallback, repeated roots across separate jobs, attachment to an existing calculation, and state-count limits;
- Q-Chem TDDFT/EOM/ADC-style states, oscillator strengths/transition dipoles when reported, unknown-method fallback, `@@@` multi-job separation, and state-count limits.

The fixtures are redistribution-safe and intentionally small. Parser tests compare typed values directly against the fixture text and expected source semantics.

### Method/convention safety

Tests verify that source method aliases normalize to a common method family while the exact source method detail remains available. Amplitude blocks keep an explicit convention. NTO readiness is restricted to explicitly approved conventions and compatible matrix dimensions; percentages and generic method-specific coefficients are not promoted automatically.

### UV–Vis mathematics

Analytic tests cover:

- Gaussian center and source peak-height convention;
- FWHM/half-height behavior;
- deterministic line summation;
- default 0.20 eV FWHM;
- invalid/non-finite width and range rejection;
- maximum grid/resource ceilings;
- dark `f=0` behavior;
- missing/negative oscillator-strength exclusions without value invention or clamping;
- positive-energy eligibility;
- energy-to-wavelength conversion using the Jacobian rather than x-axis relabelling.

### Interface parity

Tests compare shared scientific fields across the registry/Python API and the generic MCP path. CLI tests cover human, JSON and row-oriented CSV output plus PNG/SVG export. HTML report tests require embedded `ResultRecord` parity. Offline Workbench tests require the same excited-state and UV–Vis payload values as the Python analyses.

## What this evidence does not establish

The current repository evidence is not an independent cross-program benchmark of every excited-state method. In particular it does not establish universal accuracy for:

- all Gaussian, ORCA, and Q-Chem versions;
- all TDDFT/TDA functionals and response variants;
- all CIS/CIS(D), ADC, EOM, STEOM, spin-flip, multireference, core-excited, ΔSCF/MOM, PNO/local-correlation, or other method implementations;
- method-specific transition-density or NTO transformations;
- experimental absorbance/extinction coefficients or instrument line shapes.

A parser recognizing a state label or energy is not equivalent to validation of the underlying quantum-chemical method.

## Promotion gate

Promotion above Experimental requires independently generated, redistribution-safe reference cases for named source-program/method families with:

1. exact program/version and input provenance;
2. source output or an independently parsed reference;
3. explicit state/root matching rules;
4. numeric tolerances for energies, oscillator strengths, transition moments, and any method-specific vectors being claimed;
5. cross-interface parity on the same `ResultRecord`;
6. documented unsupported/ambiguous cases.

Until those gates are satisfied, user-facing documentation and returned records must continue to label these analyses **Experimental**.
