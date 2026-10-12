# Larger source-output spectroscopy examples

These nine pinned divinylbenzene outputs cover Gaussian, ORCA and Q-Chem IR,
Raman and excited-state calculations. The molecule has 20 atoms and 54
vibrational modes. The source files are downloaded rather than redistributed
in this repository. Their upstream revision and SHA-256 checksums are in
[sources.json](sources.json).

From the repository root, with the source environment active:

```bash
python -m scripts.validate_spectra_references \
  --download --input-dir /tmp/openwfn-spectra-inputs \
  --output /tmp/openwfn-spectra-reference.json
```

Choose new paths for the first run; existing files are not overwritten. On
later runs, omit `--download` and choose a new report filename.

The procedure compares frequencies, source intensities/activities, excitation
energies and oscillator strengths with independently read printed tables. It
also checks Gaussian broadening against a separate numerical expression. This
checks extraction and post-processing, not agreement with experiment or the
accuracy of the source method. Adapter source-unit conventions are retained;
this procedure does not establish cross-program intensity calibration.

Try the CLI:

```bash
openwfn /tmp/openwfn-spectra-inputs/gaussian-ir.out vibrations
openwfn /tmp/openwfn-spectra-inputs/gaussian-ir.out spectra ir --fwhm 20
openwfn /tmp/openwfn-spectra-inputs/gaussian-raman.out spectra raman --fwhm 20
openwfn /tmp/openwfn-spectra-inputs/orca-td.out excited states
openwfn /tmp/openwfn-spectra-inputs/orca-td.out spectra uvvis --fwhm 0.20
openwfn /tmp/openwfn-spectra-inputs/qchem-td.out properties
openwfn /tmp/openwfn-spectra-inputs/qchem-raman.out open
```

The IR/Raman FWHM is in cm^-1; UV-Vis FWHM is in eV. Raman activity is not a
fully modeled experimental Raman cross-section. UV-Vis uses source oscillator
strengths, not a ground-state HOMO–LUMO gap.

For Python and reproducible batch coverage:

```python
from openwfn import load

calculation = load('/tmp/openwfn-spectra-inputs/gaussian-raman.out')
result = calculation.analyze('raman-spectrum', fwhm_cm1=20.0)
print(result.data['lines'])
print(result.units)
print(result.warnings)
```

```bash
python scripts/review_workflows.py /tmp/openwfn-spectra-inputs/*.out \
  --output /tmp/openwfn-spectra-workflows.json
```

These outputs do not supply complete wavefunctions for every operation. Missing
NTO-ready matrices, AO coefficients or densities are reported explicitly. ORCA
spin-forbidden rows remain in the state table with unavailable oscillator
strength; they are not silently converted to numerical zeros. Some Q-Chem
layouts use the alternate structure reader and retain that warning.
