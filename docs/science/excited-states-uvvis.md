# Excited states and UV–Vis

openWFN treats excited-state output as **source-reported scientific data first** and derived spectrum visualization second. The current feature is **Experimental**.

## Supported source model

Gaussian, ORCA, and Q-Chem adapters normalize source output into the same typed structure:

- one or more source jobs/blocks,
- one-based openWFN state index inside each job,
- source state identifier when present,
- excitation energy in eV,
- derived wavelength in nm for positive excitation energy,
- oscillator strength when reported,
- transition dipole and its source unit when reported,
- multiplicity, symmetry, and state label when reported,
- transition/configuration contributions with an explicit quantity and convention,
- amplitude blocks with explicit mathematical convention and dimensions,
- method family/detail and parser provenance.

Missing source properties remain unavailable. openWFN does not replace missing oscillator strength or transition dipoles with zero.

## Method-general boundary

The data model can represent source states from TDHF/RPA, CIS and related variants, TDDFT/TDA, spin-flip methods, ADC families, EOM families, STEOM/local variants, CASSCF/CASPT2/NEVPT2, RAS/MRCI-style outputs, NOCI/STEX, ΔSCF/MOM, core-excited workflows, and other source-labelled states.

Representation support is not the same as claiming every method-specific transformation is implemented. A printed TDDFT X/Y vector, an EOM left/right vector, an ADC vector, and a CI percentage are not interchangeable. openWFN preserves the source convention and only marks amplitude data NTO-ready when the convention and dimensions satisfy an explicitly approved mathematical contract.

## Job and state indexing

Source files may contain multiple Link1/jobs/blocks. openWFN keeps these boundaries explicit rather than flattening roots from unrelated calculations.

```python
states = calculation.analyze("excited-states")
state = calculation.analyze("excited-state", job=2, state=1)
```

`job` and `state` are one-based. If more than one excited-state job exists, analyses that require a single job require an explicit `job=` selector.

## Source sticks

For UV–Vis, each source state remains in the stick/state table even when it cannot participate in the simulated curve.

- `f > 0`: included in the broadened optical curve.
- `f = 0`: valid dark state; retained and contributes a zero-height line.
- missing `f`: retained as unavailable and excluded from the curve.
- negative `f`: preserved exactly, never clamped to zero, and excluded from the simulated curve with a warning.
- nonpositive excitation energy: preserved in state data but excluded from the simulated optical curve.

This distinction keeps source parsing auditable.

## Gaussian broadening

The UV–Vis profile is broadened in **energy space**. The default is a Gaussian with full width at half maximum (FWHM) of **0.20 eV**.

For a line centered at energy \(E_i\) with source oscillator strength \(f_i\), openWFN uses the same peak-height-preserving Gaussian convention as its other spectrum renderers:

$$
\sigma = \frac{\mathrm{FWHM}}{2\sqrt{2\ln 2}}
$$

$$
I(E) = \sum_i f_i \exp\left[-\frac{(E-E_i)^2}{2\sigma^2}\right]
$$

This is a deterministic visualization/post-processing profile. It is **not** absorbance, molar extinction coefficient, experimental line shape, or an instrument response model.

The grid is resource bounded and rejects non-finite ranges, nonpositive width, invalid point counts, and excessive allocations before building the array.

## Energy to wavelength

The wavelength coordinate is

$$
\lambda = \frac{hc}{E}
$$

with excitation energy in eV and wavelength in nm. A wavelength-domain density cannot be obtained by simply relabelling the energy-domain x axis. openWFN applies the Jacobian:

$$
I_\lambda(\lambda)=I_E(E)\left|\frac{dE}{d\lambda}\right|
=I_E(E)\frac{hc}{\lambda^2}
$$

The wavelength arrays are therefore derived from the energy-domain curve and have their own y values.

## Transition dipoles

`transition-dipoles` exposes only source-reported vectors. Missing transition dipoles fail explicitly rather than being reconstructed from unrelated printed quantities.

## Interfaces

CLI:

```bash
openwfn calculation.log excited states
openwfn calculation.log excited state 2
openwfn calculation.log excited dipoles
openwfn calculation.log spectra uvvis --fwhm 0.20 --points 1501
```

Python:

```python
states = calculation.analyze("excited-states")
state2 = calculation.analyze("excited-state", state=2)
dipoles = calculation.analyze("transition-dipoles")
uvvis = calculation.analyze("uvvis-spectrum", fwhm_ev=0.20)
```

MCP uses the same named analyses and parameter-forwarding path. Reports and the offline Workbench render the same `ResultRecord` values; they do not run a second scientific implementation.

## Validation status

The feature remains **Experimental**. Current evidence covers:

- parser fidelity against project-owned Gaussian, ORCA, and Q-Chem source-like fixtures,
- multi-job separation,
- missing/dark/negative oscillator-strength behavior,
- transition-dipole source fidelity,
- method/convention normalization tests,
- analytic Gaussian center and FWHM behavior,
- energy-to-wavelength Jacobian tests,
- grid/resource limits,
- CLI/Python/MCP/result parity,
- report and Workbench payload parity.

Promotion above Experimental requires broader, independently generated reference evidence for named program/method families and explicit acceptance tolerances. Passing software tests alone is not sufficient.

## NTO boundary

This feature prepares the data model for future natural transition orbitals but does not claim general NTO support. Only mathematically defined, convention-approved dense transition objects can be considered NTO-ready. Printed percentages, generic configuration summaries, or method-specific vectors with insufficient semantics are not converted into NTOs.
