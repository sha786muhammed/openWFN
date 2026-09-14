---
title: Wavefunction analysis
description: Unified wavefunction post-processing for reproducible computational chemistry.
hide:
  - toc
---

<div class="ow-home" markdown="1">

<section class="ow-intro">
  <div class="ow-intro__brand" markdown="1">

<div class="ow-brand-panel">
  <img src="assets/images/openwfn-brand.svg" alt="openWFN" width="560" height="120">
</div>

<p class="ow-kicker">Wavefunction post-processing</p>

<h1>Wavefunction analysis, made reproducible.</h1>

<p class="ow-lede">A unified post-processing toolkit for turning quantum-chemistry calculations into traceable, validated, publication-ready results.</p>

<p class="ow-context">Work locally through the command line or Python, from individual calculations to high-throughput collections.</p>

<div class="ow-actions">
  <a class="ow-button ow-button--primary" href="start/first-analysis/">Run your first analysis</a>
  <a class="ow-button" href="reference/cli/">Explore the CLI</a>
</div>

<p class="ow-meta">Python 3.10–3.13 · MIT licensed · local by design</p>

  </div>
  <div class="ow-intro__command">
    <div class="ow-command-label"><span>Quick start</span><span>Terminal</span></div>
    <pre><code>python -m pip install openwfn

openwfn molecule.fchk doctor
openwfn molecule.fchk orbitals frontier
openwfn molecule.fchk report build report.html</code></pre>
    <a href="quick-start/">Installation and first steps →</a>
  </div>
</section>

## One toolkit for the complete analysis path

<p class="ow-section-intro">Keep scientific interpretation, automation, evidence, and research output connected to the same calculation record.</p>

<div class="ow-capability-grid" markdown="1">

<div class="ow-capability" markdown="1">
<span class="ow-capability__number">01</span>
### Analyze
Inspect molecular structure, orbitals, electron density, atomic populations, electrostatic potential, and derived properties.
</div>

<div class="ow-capability" markdown="1">
<span class="ow-capability__number">02</span>
### Automate
Use stable CLI commands, a typed Python model, structured results, resumable batches, and machine-readable exports.
</div>

<div class="ow-capability" markdown="1">
<span class="ow-capability__number">03</span>
### Validate
Track parser provenance, transformations, units, numerical controls, capability status, and fixture-backed evidence.
</div>

<div class="ow-capability" markdown="1">
<span class="ow-capability__number">04</span>
### Publish
Produce JSON, CSV, figures, cube files, reports, structures, and portable offline workbenches for review and reuse.
</div>

</div>

## A reproducible workflow, not a collection of scripts

<div class="ow-workflow">
<div class="ow-steps">
<div class="ow-step"><strong>Inspect</strong><span>Identify the calculation and discover which scientific records are available.</span></div>
<div class="ow-step"><strong>Analyze</strong><span>Run explicit methods with documented assumptions, units, and numerical controls.</span></div>
<div class="ow-step"><strong>Verify</strong><span>Review status, provenance, convergence, validation evidence, and known limitations.</span></div>
<div class="ow-step"><strong>Share</strong><span>Export durable results for collaborators, downstream systems, or publication.</span></div>
</div>
<div class="ow-terminal">
<div class="ow-terminal__bar"><span>Structured analysis</span><span>water.fchk</span></div>
<pre><code><span class="ow-prompt">$</span> openwfn water.fchk doctor
Status: Stable
Capabilities: basis, orbitals, density

<span class="ow-prompt">$</span> openwfn water.fchk orbitals frontier
HOMO       -0.477229 hartree
LUMO        0.261095 hartree
Gap         0.738323 hartree

<span class="ow-prompt">$</span> openwfn batch ./calculations --analysis summary \
    --analysis frontier --output-dir ./results</code></pre>
</div>
</div>

## Trust is visible

<p class="ow-section-intro">Each capability has an explicit evidence boundary. Successful execution alone is not presented as universal scientific validation.</p>

<div class="ow-proof-strip">
  <div class="ow-proof ow-proof--stable"><strong>Stable</strong><span>Implemented and regression tested</span></div>
  <div class="ow-proof ow-proof--validated"><strong>Validated</strong><span>Quantitative evidence for named fixtures</span></div>
  <div class="ow-proof ow-proof--experimental"><strong>Experimental</strong><span>Available with documented caution</span></div>
  <div class="ow-proof ow-proof--unsupported"><strong>Unsupported</strong><span>Required records, method, or evidence are absent</span></div>
</div>

<p class="ow-evidence-links"><a href="science/validation-status/">Review the Validation matrix</a> · <a href="limitations/">Understand the Limitations</a> · <a href="methods/">Read the Methods</a></p>

<section class="ow-support" markdown="1">

## Current support, stated precisely

openWFN currently performs its full electronic wavefunction analysis from Gaussian formatted-checkpoint data. Structure-only records can also enter through XYZ, MOL/SDF, and PDB parsers. The internal model and parser boundaries are designed for additional quantum-chemistry formats, but a format is not advertised as supported until its parser and validation evidence are shipped.

[See formats and exports](reference/formats-and-exports.md) · [Follow format development](https://github.com/sha786muhammed/openWFN/issues)

</section>

## Start from your role

<div class="ow-paths">
  <div class="ow-path"><strong>For researchers</strong><p>Examine methods, evidence, provenance, reproducible reports, limitations, and Citation guidance.</p><a href="start/learning-paths/#researcher-path">Research workflow →</a></div>
  <div class="ow-path"><strong>For students</strong><p>Build concepts from coordinates and orbitals through density, charges, and electrostatic potential.</p><a href="start/learning-paths/#student-path">Learning path →</a></div>
  <div class="ow-path"><strong>For developers</strong><p>Integrate the Python model or extend parsers, analyses, exporters, and validation fixtures.</p><a href="start/learning-paths/#developer-path">Developer path →</a></div>
</div>

<div class="ow-closing">
  <strong>From calculated wavefunctions to trustworthy scientific evidence.</strong>
  <span><a href="start/first-analysis/">Get started</a> · <a href="citation/">Citation</a> · <a href="https://github.com/sha786muhammed/openWFN">GitHub</a></span>
</div>

</div>
