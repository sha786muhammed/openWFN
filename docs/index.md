---
title: Wavefunction analysis
description: Wavefunction and quantum-chemistry post-processing with CLI, Python, MCP and local chat.
hide:
  - toc
---

<div class="ow-home" markdown="1">
<section class="ow-intro ow-intro--workspace">
  <div class="ow-intro__brand" markdown="1">

<div class="ow-brand-panel">
  <img src="assets/images/openwfn-brand.svg" alt="openWFN" width="560" height="120">
</div>

<p class="ow-kicker">Quantum-chemistry post-processing</p>

<h1>Wavefunction analysis, made reproducible.</h1>

<p class="ow-lede">One scientific engine. From quantum-chemistry files to meaningful results.<br>Use the CLI, Python, MCP or chat.</p>

<p class="ow-context">Wavefunctions · Grids · QC outputs · Structures</p>

<div class="ow-actions">
  <a class="ow-button ow-button--primary" href="start/first-analysis/">Get started</a>
</div>

<p class="ow-meta">Python 3.10–3.13 · MIT project code · local analysis</p>

  </div>
</section>

<div class="ow-workspace-preview" markdown="0">
<section class="ow-intro__command ow-workspace-preview__cli" aria-label="Guided CLI example">
<div class="ow-command-label"><span>Guided CLI</span><span>Example workflow</span></div>
<div class="ow-terminal-brand"><img src="assets/images/openwfn-brand.svg" alt="openWFN" width="168" height="36"><span>Quantum-chemistry post-processing</span></div>
<pre><code>openwfn molecule.molden open

Choose → Configure → Run → Review → Save

Density / Integrate
Check the electron count before exporting density.

Density kind     Total
Grid spacing     0.15 bohr
Padding          6 bohr
Save folder      results/

Review grid convergence before using the result.</code></pre>
<a href="guides/cli-workflows/">Explore the guided workflow →</a>
</section>
<section class="ow-intro__command" aria-label="Scientific assistant example">
<div class="ow-command-label"><span>Scientific assistant</span><span>Example conversation</span></div>
<pre><code>openwfn molecule.molden chat

› Can I get an IR spectrum?

If the file has no frequencies or IR intensities,
the assistant explains what is missing.

Open a frequency-calculation output to check
for IR data. No spectrum is invented.

/open  /model  /save  /details</code></pre>
<a href="assistant/">Connect a model or ask about your file →</a>
</section>
</div>

Analyse one calculation or a collection of files. Start with
`openwfn FILE capabilities` to see which analyses your file supports.

## Choose how you work

<div class="ow-capability-grid" markdown="1">

<div class="ow-capability" markdown="1">
<span class="ow-capability__number">CLI</span>
### Guided or direct
Open a file, choose an available analysis and adjust its settings. Use direct commands in scripts.
[CLI reference](reference/cli.md)
</div>

<div class="ow-capability" markdown="1">
<span class="ow-capability__number">Python</span>
### Use the API
Load a supported file and get results with units, warnings and a record of the source.
[Python API](reference/python-api.md)
</div>

<div class="ow-capability" markdown="1">
<span class="ow-capability__number">MCP</span>
### Connect a local client
Expose read-only analyses inside a chosen input directory. Inspect capabilities before requesting a property.
[MCP setup](mcp.md)
</div>

<div class="ow-capability" markdown="1">
<span class="ow-capability__number">Chat</span>
### Ask a scientific question
Ask file questions backed by openWFN results, or connect a model for general scientific conversation. Model explanations are labelled separately. No model is downloaded automatically.
[Scientific assistant](assistant.md)
</div>

</div>

## Start with the data in your file

<section class="ow-support" markdown="1">

| Input family | What to check |
| --- | --- |
| FCHK/FCH, Molden/`.molden.input`, WFN, WFX, MWFN, MKL | Basis, orbitals, density and electronic state actually present |
| Cube/CUB | Stored field, axes and units; a grid is not a complete wavefunction |
| Gaussian, ORCA and Q-Chem LOG/OUT | Source-reported properties and available spectroscopy records |
| XYZ, PDB, MOL, SDF | Structure and supported formal-charge records; no inferred wavefunction |

Binary Gaussian `.chk` needs the separately installed Gaussian `formchk`
utility. A successful parse does not make every analysis available.
[Formats and exports](reference/formats-and-exports.md) lists supported files and their limits.

</section>

## Check the result before using it

Results show values and units first. Important warnings remain visible;
Details and JSON preserve diagnostics, validation status and provenance.
Unknown charge, spin or convergence is not guessed.
Density settings must be converged for the property and system being studied.

[Methods](methods.md) · [Validation evidence](science/validation-status.md) ·
[Limitations](limitations.md)

<div class="ow-closing">
  <strong>Keep the input hash, settings and complete result with your analysis.</strong>
  <span><a href="citation/">Citation</a> · <a href="project/contributing/">Contributing</a> · <a href="https://github.com/sha786muhammed/openWFN">GitHub</a></span>
</div>
</div>
