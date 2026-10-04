# Vibrational spectroscopy validation record

Current status: **Experimental**.

This directory records the scientific boundary for the native Gaussian harmonic vibrational/IR/Raman feature. The committed implementation tests verify parsing, units, deterministic Gaussian broadening, missing-data behavior, and cross-interface parity. They do not yet constitute an independent external validation campaign.

## What is currently checked

- Gaussian frequency blocks are parsed into typed mode records with signed frequencies.
- Imaginary modes remain signed and are excluded from broadened physical spectra with an explicit warning.
- IR intensity and Raman activity remain distinct source quantities.
- The Gaussian broadening function reaches half height at plus/minus FWHM/2 for an isolated line.
- Missing Raman data or missing normal-mode vectors remain unavailable instead of being invented.
- Python API, MCP, CLI/report payloads, and Workbench payloads use the same registered numerical results.

Primary regression evidence:

- `tests/parsers/test_gaussian_output.py`
- `tests/unit/test_vibrational_analysis.py`
- `tests/integration/test_vibrational_parity.py`
- `tests/cli/test_vibrational_spectroscopy.py`
- `tests/integration/test_vibrational_report.py`
- `tests/integration/test_vibrational_workbench.py`

Fixtures live under `tests/fixtures/gaussian/vibrations/` and are deliberately small parser/regression excerpts. They are not presented as an independently generated benchmark corpus.

## What is not yet established

The feature is not promoted to Validated because the repository does not yet contain a provenance-complete independent comparison across a declared molecule/method/program scope with fixed acceptance tolerances. In particular, current evidence does not validate:

- all Gaussian versions or output variants;
- other quantum-chemistry programs;
- anharmonic frequencies;
- thermochemical interpretation;
- experimental peak positions or line shapes;
- Raman activity-to-intensity conversion;
- arbitrary normal-coordinate conventions across programs.

A future promotion should add redistribution-safe reference calculations, exact software/method/basis provenance, an independent reader or reference implementation, fixed numerical tolerances, and a permanent generated comparison report. Until then every new spectroscopy `ResultRecord` remains `validation_status="Experimental"`.
