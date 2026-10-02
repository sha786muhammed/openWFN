# The offline molecular workbench

The workbench packages a calculation, selected derived data, interface code, and the molecular renderer into one HTML file. It is designed for inspection, teaching, and sharing when a hosted service is unnecessary or inappropriate.

**Status: Stable interface for the documented desktop Chromium scope.** The workbench is an optional visualization and teaching surface, not a numerical reference. Preserve the corresponding JSON, CSV, or report output as the scientific record.

```bash
openwfn ./openwfn-examples/water.fchk workbench water-workbench.html --open
```

This example assumes `openwfn examples install ./openwfn-examples` has already
been run. Without `--open`, open the resulting file in a modern browser. It
works through `file://`; no localhost server or openWFN process must remain
running.

## What the file contains

The export can include molecular coordinates, bonds, calculation provenance, analysis properties, volumetric fields, CSS, JavaScript, and the vendored 3D rendering engine. This portability has a privacy consequence: anyone who receives the file can inspect its embedded molecular data. Do not publish a workbench generated from a confidential calculation.

Molecular rendering is provided by [3Dmol.js](https://github.com/3dmol/3Dmol.js)
under the BSD-3-Clause license. The renderer and its attribution are embedded in
the output, so opening a workbench does not fetch the library from a CDN.

## Workspace tour

### Structure

Rotate, zoom, and recenter the molecule; switch rendering style; show or hide atom labels; and inspect atom identity. Bond display follows openWFN's geometry-based connectivity model and should not be interpreted as a calculated bond order.

### Orbitals

Inspect available frontier information and, when the calculation contains compatible coefficients and basis data, orbital fields. Positive and negative phases are represented separately; color indicates phase, not charge.

### Density and ESP

Review total, alpha, beta, or spin-density fields together with isovalue and grid provenance. Embedded coarse grids are visualization data unless separately converged and validated. Grid-derived electronic and total ESP remain Experimental; do not remove that qualification in screenshots or reports.

### Measurements

Select two atoms for a distance, three for an angle, or four for a signed dihedral. Selection order matters, especially for the torsion sign. CLI atom numbering is one-based.

## A careful review workflow

1. Run `doctor` and `summary` in the terminal.
2. Generate the workbench under a new, descriptive filename.
3. Confirm molecular charge, multiplicity, formula, and atom ordering.
4. Compare at least one displayed value with machine-readable CLI output.
5. Check the capability label and grid settings for every electronic surface.
6. Preserve the exact openWFN version and input checksum with the artifact.

## Workbench versus report

Use a **workbench** for interactive spatial exploration. Use a **report** for a fixed research record with selected analyses and command provenance. Archive machine-readable tables as well; neither the workbench nor a screenshot should be the sole numerical record.

## Troubleshooting

- If the browser does not open, omit `--open` and open the reported HTML path manually.
- If a panel has no data, run `doctor`; the source FCHK may lack required records.
- If generation refuses to replace a file, choose a new filename or deliberately add the global `--overwrite` option before the input file.
- If a surface is slow, use coarser exploratory data first, then converge settings separately.

See [Formats and exports](reference/formats-and-exports.md), [Security](project/security.md), and [Validation status](science/validation-status.md).

## Browser validation scope

The development branch validates all eleven committed everyday-QC molecules in
offline Chromium 151.0.7922.34, with workspace/surface control interaction and
21 distance/angle/signed-torsion readouts matching the Python API. The canvas
is contained in the viewer so it cannot intercept sidebar clicks.
Evidence with input/CI provenance is captured in
`validation/everyday-qc/browser-report.json`; CI reruns the browser validator.
This scope does not certify every GPU, browser or mobile device. Each preview
field retains its scientific validation and conservation status independently
of the interface. Coarse density fields are partial and explicitly warn about
failed integration; use convergence-controlled density export for quantitative
integration. The ESP preview is the named Mulliken charge model; Gaussian-integral
point ESP is available through the CLI/API and guided terminal.
