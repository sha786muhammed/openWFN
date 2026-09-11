---
title: Reproducible wavefunction analysis
description: Learn, run, and verify Gaussian wavefunction analysis with openWFN.
hide:
  - toc
---

<p class="ow-eyebrow">Open computational chemistry</p>

# From checkpoint data to defensible molecular insight.

<p class="ow-lede">openWFN is a transparent command-line, Python, reporting, and offline 3D workbench for Gaussian wavefunction analysis. Learn the science, run a reproducible workflow, and inspect the assumptions behind every result.</p>

<div class="ow-actions">
  <a class="ow-button ow-button--primary" href="start/first-analysis/">Begin with the fundamentals</a>
  <a class="ow-button" href="reference/cli/">Open the reference</a>
</div>

![Translucent red-orange and blue molecular orbital lobes surrounding a small ball-and-stick molecule](assets/images/openwfn-orbital-hero.webp){ loading=lazy width=1400 height=1050 }

<div class="ow-paths">
  <div class="ow-path">
    <span class="ow-eyebrow">Analyze</span>
    <strong>For researchers</strong>
    <p>Evaluate methods, validation evidence, limitations, provenance, reports, and citation guidance before using a result.</p>
    <a href="start/learning-paths/#researcher-path">Follow the researcher path</a>
  </div>
  <div class="ow-path">
    <span class="ow-eyebrow">Learn</span>
    <strong>For students</strong>
    <p>Build concepts from coordinates and orbitals through density, atomic charges, and electrostatic potential.</p>
    <a href="start/learning-paths/#student-path">Follow the student path</a>
  </div>
  <div class="ow-path">
    <span class="ow-eyebrow">Build</span>
    <strong>For developers</strong>
    <p>Use the Python API, understand the typed calculation model, and extend parsers, analyses, and exporters.</p>
    <a href="start/learning-paths/#developer-path">Follow the developer path</a>
  </div>
</div>

## Learn. Run. Verify.

1. **Learn concepts.** Begin with [wavefunction-analysis foundations](start/index.md) and the [core terminology](start/terminology.md).
2. **Run workflows.** Follow the [first analysis](start/first-analysis.md), then continue through geometry, orbitals, density, population analysis, ESP, reports, and the workbench.
3. **Verify results.** Read the [Validation](validation.md), [Limitations](limitations.md), and [Scientific methods](methods.md) before drawing research conclusions.

## A reproducible first analysis

```bash
python -m pip install --upgrade openwfn
openwfn water.fchk summary
openwfn water.fchk workbench water-workbench.html --open
```

The same calculation model powers the direct CLI, guided terminal, Python API,
structured reports, and portable offline workbench. Your molecular data remains on
your computer unless you choose to share an exported file.

[Follow the complete first-analysis tutorial](start/first-analysis.md)

## What openWFN analyzes

| Area | Available work | Read next |
| --- | --- | --- |
| Molecular structure | coordinates, distances, angles, dihedrals, bonds, fragments | [Geometry tutorial](tutorials/geometry.md) |
| Molecular orbitals | energies, occupations, HOMO, LUMO, frontier gap | [Orbitals and density](tutorials/orbitals-density.md) |
| Electron density | density matrices, point evaluation, integration, cube export | [Scientific methods](methods.md) |
| Atomic populations | Mulliken and symmetric Löwdin populations and charges | [Validation](validation.md) |
| Electrostatic potential | nuclear, charge-model, and grid-derived point potentials | [Limitations](limitations.md) |
| Research outputs | JSON, CSV, Markdown, HTML reports, structures, images | [Reports tutorial](tutorials/reports.md) |

## Know the evidence boundary

<span class="ow-status ow-status--stable"><strong>Stable</strong> — implemented and tested within documented assumptions.</span>

<span class="ow-status ow-status--validated"><strong>Validated</strong> — supported by the active provenance-backed quantitative validation set.</span>

<span class="ow-status ow-status--experimental"><strong>Experimental</strong> — implemented but awaiting broader scientific validation. Grid-derived electronic and total ESP remain here.</span>

<span class="ow-status ow-status--unsupported"><strong>Unsupported</strong> — required records, algorithms, or scientific evidence are absent.</span>

Review the [validation matrix](validation.md) and [documented limitations](limitations.md) for the exact status of each capability.

## Open, local, and citable

- **Open source:** MIT licensed, with public tests and implementation.
- **Local by design:** calculations and exported workbench files run on your computer.
- **Reproducible:** reports record inputs, parameters, software version, and provenance.
- **Citable:** use the [Citation](citation.md) guide to identify the exact release.

Current release: **openWFN 0.7.0** · [Release notes](releases/0.7.0.md) · [GitHub repository](https://github.com/sha786muhammed/openWFN)
