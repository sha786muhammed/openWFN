# The offline molecular workbench

The workbench packages a calculation, selected derived data, interface code, and the molecular renderer into one HTML file. It is designed for inspection, teaching, and sharing when a hosted service is unnecessary or inappropriate.

**Status: Stable interface for the documented desktop Chromium scope.** The workbench is an optional visualization and teaching surface, **not a numerical reference**. Preserve the corresponding machine-readable JSON, CSV, or report output as the scientific record. A newly displayed analysis keeps its own scientific validation status; adding it to a Stable interface does not promote its scientific status.

```bash
openwfn ./openwfn-examples/water.fchk workbench water-workbench.html --open
```

For a Gaussian frequency output containing typed vibrational records:

```bash
openwfn water_freq.log workbench water-vibrations.html --open
```

Without `--open`, open the resulting file in a modern browser. It works through `file://`; no localhost server or openWFN process must remain running.

## What the file contains

The export can include molecular coordinates, bonds, calculation provenance, analysis properties, volumetric fields, vibrational mode records, CSS, JavaScript, and the molecular renderer. This portability has a privacy consequence: anyone who receives the file can inspect its embedded molecular data. Do not publish a workbench generated from a confidential calculation.

Molecular rendering is provided by [3Dmol.js](https://github.com/3dmol/3Dmol.js) under the BSD-3-Clause license. The renderer and its attribution are embedded in the output, so opening a workbench does not fetch the library from a CDN.

## Workspace tour

### Structure

Rotate, zoom, and recenter the molecule and inspect atom identity. Bond display follows openWFN's geometry-based connectivity model and should not be interpreted as a calculated bond order.

### Orbitals

Inspect available frontier information and, when the calculation contains compatible coefficients and basis data, orbital fields. Positive and negative phases are represented separately; color indicates phase, not charge.

### Vibrations

When the input contains native vibrational records, the Workbench adds a **Vibrations** workspace. It embeds the same registered `vibrations`, `ir-spectrum`, `raman-spectrum`, and `normal-mode` results used by the Python API.

The workspace provides:

- a mode selector showing one-based mode number and signed source frequency;
- source mode metadata, including IR intensity and Raman activity when available;
- embedded IR and Raman-activity curves from the same deterministic broadened arrays used elsewhere;
- clickable source spectral sticks that select the corresponding mode;
- displacement arrows when source Cartesian normal-mode vectors are present;
- an amplitude control that changes **only arrow length for display**.

The amplitude control does not alter or renormalize source displacement vectors, frequencies, reduced masses, force constants, IR intensities, or Raman activities. If displacement vectors are absent, the workspace says so explicitly; it does not synthesize motion.

The spectroscopy calculations remain **Experimental** even though the Workbench interface itself is Stable. Gaussian Raman values are displayed as Raman **activities**, not converted experimental intensities. See [Vibrational spectroscopy](science/vibrational-spectroscopy.md).

### Density and ESP

Review available density/ESP fields together with isovalue and grid provenance. Embedded coarse grids are visualization data unless separately converged and validated. Grid-derived electronic/total ESP remain Experimental; do not remove that qualification in screenshots or reports.

### Measurements

Select two atoms for a distance, three for an angle, or four for a signed dihedral. Selection order matters, especially for the torsion sign. CLI atom numbering is one-based.

## A careful review workflow

1. Run `doctor` and `summary` in the terminal.
2. For spectroscopy, run `vibrations` and the desired `spectra` command and preserve JSON/CSV output.
3. Generate the Workbench under a new, descriptive filename.
4. Confirm molecular charge, multiplicity, formula, atom ordering, and selected mode number.
5. Compare at least one displayed value with machine-readable CLI/Python output.
6. Check the capability and validation label for every displayed scientific result or field.
7. Preserve the exact openWFN version and input checksum with the artifact.

## Workbench versus report

Use a **workbench** for interactive spatial exploration. Use a **report** for a fixed research record with selected analyses and command provenance. Archive machine-readable tables as well; neither the workbench nor a screenshot should be the sole numerical record.

For vibrational work, the Workbench is particularly useful for connecting a selected source spectral line with a 3D normal-mode direction, while the report is better for fixed mode tables and plots.

## Troubleshooting

- If the browser does not open, omit `--open` and open the reported HTML path manually.
- If a panel has no data, run `doctor`; the source file may lack required records.
- If the Vibrations workspace is absent, the parsed input contains no typed vibrational record.
- If spectra exist but arrows do not, source displacement vectors are missing; this is a supported unavailable state.
- If generation refuses to replace a file, choose a new filename or deliberately add the global `--overwrite` option before the input file.
- If a volumetric surface is slow, use coarser exploratory data first, then converge settings separately.

See [Formats and exports](reference/formats-and-exports.md), [Security](project/security.md), and [Validation status](science/validation-status.md).

## Browser validation scope

The stable Workbench line validates the established everyday-QC workspaces in offline desktop Chromium with workspace/surface interaction and geometry readouts matching the Python API. The canvas is contained in the viewer so it cannot intercept sidebar clicks. Evidence with input/CI provenance is captured in `validation/everyday-qc/browser-report.json`; CI reruns the browser validator.

The vibrational feature additionally has payload/HTML contract tests that require the Workbench to reuse registered spectroscopy numerical data and to represent missing displacement vectors explicitly. Browser CI remains the gate for preserving existing workspaces as the Vibrations workspace is added. This scope does not certify every GPU, browser, or mobile device.

Each preview field retains its scientific validation and conservation status independently of the interface. Coarse density fields are partial when their integration diagnostic fails. The Vibrations workspace likewise preserves Experimental spectroscopy status; interface rendering is not independent scientific validation.
