---
title: Wavefunction analysis
description: Wavefunction and quantum-chemistry post-processing with CLI, Python, MCP and local chat.
hide:
  - toc
---

!!! note "Release preparation"

    This checkout prepares 0.12.0. The published release is still 0.11.0 until
    [release checks](releases/0.12.0.md) pass. New guided/chat features require
    this checkout before publication.

<div class="ow-home" markdown="1">
<section class="ow-intro">
  <div class="ow-intro__brand" markdown="1">

<div class="ow-brand-panel">
  <img src="assets/images/openwfn-brand.svg" alt="openWFN" width="560" height="120">
</div>

<p class="ow-kicker">Quantum-chemistry post-processing</p>

<h1>Wavefunction analysis, made reproducible.</h1>

<p class="ow-lede">Wavefunction post-processing for quantum chemistry. Use the same scientific engine from the CLI, Python, MCP or terminal chat.</p>

<p class="ow-context">Analyze individual calculations and high-throughput collections. The available properties depend on the records in each file.</p>

<div class="ow-actions">
  <a class="ow-button ow-button--primary" href="start/first-analysis/">Start an analysis</a>
  <a class="ow-button" href="reference/formats-and-exports/">Check file support</a>
</div>

<p class="ow-meta">Python 3.10–3.13 · MIT project code · local analysis</p>

  </div>
  <div class="ow-intro__command">
    <div class="ow-command-label"><span>Guided CLI</span><span>Terminal</span></div>
    <pre><code># Release-preparation checkout:
python -m pip install -e .

openwfn molecule.molden open
openwfn molecule.molden capabilities

# A script-friendly result
openwfn --format json molecule.molden summary</code></pre>
    <a href="installation/">Installation and model setup →</a>
  </div>
</section>

## Choose how you work

<div class="ow-capability-grid" markdown="1">

<div class="ow-capability" markdown="1">
<span class="ow-capability__number">CLI</span>
### Guided or direct
Open a file, choose an eligible workflow and adjust its settings. Use explicit commands for scripts.
[CLI reference](reference/cli.md)
</div>

<div class="ow-capability" markdown="1">
<span class="ow-capability__number">Python</span>
### Use the API
Load supported files and obtain versioned results with units, warnings and source provenance.
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
A configured model selects a tool; openWFN supplies the values and explanations. No model is downloaded automatically.
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
[Formats and exports](reference/formats-and-exports.md) explain the tested contract.

</section>

## Check the result before using it

<div class="ow-proof-strip">
  <div class="ow-proof ow-proof--stable"><strong>Stable</strong><span>Documented, regression-tested interface</span></div>
  <div class="ow-proof ow-proof--validated"><strong>Validated</strong><span>Numerical evidence for a named scope</span></div>
  <div class="ow-proof ow-proof--experimental"><strong>Experimental</strong><span>Independent validation is incomplete</span></div>
  <div class="ow-proof ow-proof--unsupported"><strong>Unsupported</strong><span>The required data or method is unavailable</span></div>
</div>

Execution status and scientific validation are separate. A `partial` result
keeps its warnings. Unknown charge, spin or convergence is not guessed.
Density settings must be converged for the property and system being studied.

[Methods](methods.md) · [Validation evidence](science/validation-status.md) ·
[Limitations](limitations.md)

<div class="ow-closing">
  <strong>Keep the input hash, settings and complete result with your analysis.</strong>
  <span><a href="citation/">Citation</a> · <a href="project/contributing/">Contributing</a> · <a href="https://github.com/sha786muhammed/openWFN">GitHub</a></span>
</div>
</div>
