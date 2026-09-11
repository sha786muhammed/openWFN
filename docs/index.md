---
title: openWFN
description: Reproducible Gaussian wavefunction analysis from the CLI, Python API, reports, and an offline 3D workbench.
hide:
  - toc
---

<div class="ow-home" markdown="1">

<section class="ow-hero">
  <div class="ow-hero__copy" markdown="1">

<img class="ow-brand-lockup" src="assets/images/openwfn-wordmark.png" alt="openWFN — Wavefunction Analysis" width="620" height="230">

<h1>Wavefunction analysis you can inspect, reproduce, and trust.</h1>

<p class="ow-lede">openWFN is an open, reproducible wavefunction analysis toolkit for computational chemistry. It turns Gaussian formatted-checkpoint data into molecular geometry, orbitals, electron density, atomic populations, electrostatic potential, reports, and a portable 3D workbench—without sending research data to a remote service.</p>

<div class="ow-actions">
  <a class="ow-button ow-button--primary" href="start/first-analysis/">Get started</a>
  <a class="ow-button" href="reference/cli/">Explore the CLI</a>
</div>

<p class="ow-meta">Python 3.10–3.13 · MIT licensed · openWFN 0.7.0</p>

  </div>
  <div class="ow-hero__visual">
    <img src="assets/images/openwfn-orbital-hero.webp" alt="Translucent red and blue molecular orbital lobes surrounding a ball-and-stick molecule" width="1400" height="1050">
  </div>
</section>

## One workbench, every stage of analysis

<p class="ow-section-intro">Begin with the structure, move into electronic properties, and preserve every result in a form that can be checked later.</p>

<div class="ow-feature-grid" markdown="1">

<div class="ow-feature" markdown="1">
:material-ruler-square:
### Geometry
Distances, angles, signed dihedrals, covalent-radius bonds, and connected fragments.
</div>

<div class="ow-feature" markdown="1">
:material-orbit-variant:
### Orbitals
Alpha or beta frontier levels, HOMO, LUMO, occupations, and energy-gap reporting.
</div>

<div class="ow-feature" markdown="1">
:material-blur:
### Electron density
Total, alpha, beta, and spin-density evaluation, integration, and cube export.
</div>

<div class="ow-feature" markdown="1">
:material-chart-bubble:
### Population analysis
Mulliken and symmetric Löwdin populations with model-dependent atomic charges.
</div>

<div class="ow-feature" markdown="1">
:material-flash:
### Electrostatic potential
Nuclear, charge-model, and experimental grid-derived point potentials.
</div>

<div class="ow-feature" markdown="1">
:material-file-chart:
### Research output
JSON, CSV, figures, structures, batch manifests, reports, and offline visualization.
</div>

</div>

## From a file to a reproducible result

<div class="ow-workflow">
<div class="ow-steps">
<div class="ow-step"><strong>1 · Inspect</strong><span>Confirm molecular identity and discover which scientific records are available.</span></div>
<div class="ow-step"><strong>2 · Analyze</strong><span>Run explicit commands with documented units, assumptions, and numerical controls.</span></div>
<div class="ow-step"><strong>3 · Verify</strong><span>Check capability status, convergence, limitations, and provenance before interpretation.</span></div>
<div class="ow-step"><strong>4 · Share</strong><span>Export machine-readable evidence, a fixed report, or a portable local workbench.</span></div>
</div>
<div class="ow-terminal">
<div class="ow-terminal__bar"><span>Terminal</span><span>water.fchk</span></div>
<pre><code><span class="ow-prompt">$</span> openwfn water.fchk doctor
Doctor
Input: water.fchk
Capabilities: {'basis': True, 'orbitals': True, 'density': True}
Status: Stable

<span class="ow-prompt">$</span> openwfn water.fchk orbitals frontier
HOMO       -0.477229 hartree
LUMO        0.261095 hartree
Gap         0.738323 hartree

<span class="ow-prompt">$</span> openwfn water.fchk workbench water.html</code></pre>
</div>
</div>

## Evidence is part of the interface

<p class="ow-section-intro">Every capability carries an explicit evidence boundary. A command completing successfully is not, by itself, a claim of universal scientific validity.</p>

<div class="ow-proof-strip">
  <div class="ow-proof ow-proof--stable"><strong>Stable</strong><span>Implemented and regression tested</span></div>
  <div class="ow-proof ow-proof--validated"><strong>Validated</strong><span>Quantitative evidence for named fixtures</span></div>
  <div class="ow-proof ow-proof--experimental"><strong>Experimental</strong><span>Usable with documented caution</span></div>
  <div class="ow-proof ow-proof--unsupported"><strong>Unsupported</strong><span>Missing records, method, or evidence</span></div>
</div>

[Review the Validation matrix](science/validation-status.md) · [Understand the Limitations](limitations.md)

## Choose your path

<div class="ow-paths">
  <div class="ow-path"><strong>For researchers</strong><p>Evaluate methods, numerical evidence, provenance, reports, and citation guidance.</p><a href="start/learning-paths/#researcher-path">Research workflow →</a></div>
  <div class="ow-path"><strong>For students</strong><p>Build concepts from coordinates and orbitals through density, charges, and ESP.</p><a href="start/learning-paths/#student-path">Learning path →</a></div>
  <div class="ow-path"><strong>For developers</strong><p>Use the typed Python model and extend parsers, analyses, exporters, and tests.</p><a href="start/learning-paths/#developer-path">Developer path →</a></div>
</div>

## Local by design

Scientific computation happens on your computer. Generated reports, cube files, and HTML workbenches can still contain unpublished molecular data, so treat them with the same controls as the source calculation. Read [Security and data privacy](project/security.md).

**From checkpoint data to defensible molecular insight.**

**Current release:** openWFN 0.7.0 · [Release notes](releases/0.7.0.md) · [Citation](citation.md) · [GitHub](https://github.com/sha786muhammed/openWFN)

</div>
