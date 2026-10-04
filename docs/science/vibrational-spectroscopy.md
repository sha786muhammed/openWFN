# Vibrational spectroscopy

**Status: Experimental.** This page documents the native Gaussian frequency/IR/Raman workflow on the vibrational-spectroscopy feature line. The implementation is source-faithful and reproducible, but the current committed fixtures and cross-interface tests are not an independent external scientific validation campaign. Do not relabel these analyses as Validated until such evidence is added with a stated scope and tolerance.

## What openWFN reads

For supported Gaussian text output, openWFN records each printed normal mode as typed data:

- one-based mode number;
- signed frequency in cm^-1;
- whether the frequency is imaginary;
- symmetry label when printed;
- reduced mass in amu;
- force constant in mDyne/angstrom;
- IR intensity in km/mol when printed;
- Raman activity in angstrom^4/amu when printed;
- Cartesian displacement vectors when printed.

The geometry associated with the vibrational block is retained without inventing basis, orbital, or density records that are absent from the output file. Missing quantities remain unavailable.

## Analyses

The registered analyses are:

| Analysis | Result |
|---|---|
| `vibrations` | Source-reported mode table and capability flags |
| `normal-mode` | Metadata and Cartesian displacement vectors for one one-based mode |
| `ir-spectrum` | Source IR sticks plus deterministic Gaussian-broadened visualization curve |
| `raman-spectrum` | Source Raman-activity sticks plus deterministic Gaussian-broadened activity curve |

All use the shared `ResultRecord` envelope, so CLI, Python, MCP, HTML report, and Workbench views preserve the same scientific values, units, warnings, provenance, and validation label.

## Broadening convention

Broadening is a visualization/post-processing operation, not a new quantum-chemical calculation. For a source line with center $\tilde{\nu}_i$, source strength $A_i$, and requested full width at half maximum $w$, openWFN uses a Gaussian whose peak height equals the source strength:

$$
I(\tilde{\nu}) = \sum_i A_i \exp\left[-4\ln 2\left(\frac{\tilde{\nu}-\tilde{\nu}_i}{w}\right)^2\right].
$$

Therefore a single isolated peak reaches half its source height at $\tilde{\nu}_i \pm w/2$. The default FWHM is 20 cm^-1. The requested range and point count are preserved in the result metadata.

The source stick table is always kept separately from the broadened array. Plotting or changing FWHM never alters the original frequencies or source strengths.

## Imaginary modes

Imaginary modes are scientifically significant diagnostics and are never silently converted into positive-frequency peaks. openWFN keeps their signed frequencies and marks them `imaginary=true` in source mode/stick data. They are excluded from the broadened physical IR/Raman curve and the result emits an explicit warning.

An imaginary frequency can reflect a transition state, an unconverged/minimum-search problem, a soft coordinate, or another calculation-specific situation. openWFN reports the source result; interpreting the cause remains part of the underlying quantum-chemistry analysis.

## IR intensity versus Raman activity

Gaussian `IR Inten` values are carried as IR intensities in km/mol.

Gaussian `Raman Activ` values are carried as **Raman activities** in angstrom^4/amu. Activity is not the same quantity as an experimental Raman intensity. Converting activity into an intensity requires additional choices such as excitation frequency, temperature/population treatment, and convention-dependent factors. openWFN therefore does **not** silently perform that conversion.

The `raman-spectrum` broadened y values remain broadened Raman activity. UI labels, JSON units, plots, and reports preserve that distinction.

## Normal-mode visualization

When Cartesian vectors are present, the Workbench can display arrows for a selected mode. Its amplitude slider is explicitly display-only: it multiplies arrow length for visibility and does not modify the stored source displacement vectors, frequency, mass, force constant, IR intensity, or Raman activity.

If vectors are absent, mode/spectrum analysis can still be available while motion visualization is marked unavailable. openWFN does not synthesize normal-mode vectors.

## Reproducible use

CLI examples:

```bash
openwfn frequency.log vibrations
openwfn --format json frequency.log vibrations mode 2
openwfn frequency.log spectra ir --fwhm 20 --points 2001 --export ir.csv
openwfn frequency.log spectra raman --export raman.svg
```

Python examples:

```python
import openwfn

calc = openwfn.load("frequency.log")
modes = calc.analyze("vibrations")
ir = calc.analyze("ir-spectrum", fwhm_cm1=20.0, points=2001)
mode_2 = calc.analyze("normal-mode", mode=2)
```

For automation, prefer JSON/Python/MCP structured results rather than scraping terminal tables. Preserve source files, checksums, openWFN version, parameters, result status, validation status, warnings, and units with published work.

## Current validation boundary

The current feature verifies parser behavior, analytic broadening behavior, missing-data failure modes, interface parity, report payload parity, and Workbench payload parity using committed fixtures and regression tests. That establishes implementation consistency; it does **not** by itself establish independent agreement with another vibrational-analysis implementation across programs, methods, molecules, anharmonic models, or Raman experimental conditions.

Promotion beyond Experimental should require permanent provenance-complete reference cases, an independent comparison procedure, fixed tolerances, and explicit supported-program/version scope. See [Validation status](validation-status.md) and the project [everyday-QC validation record](../project/everyday-qc-validation.md).
