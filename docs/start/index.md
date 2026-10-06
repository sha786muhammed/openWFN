# Start here

openWFN post-processes supported quantum-chemistry files. Use the guided CLI,
direct commands, Python, local MCP or a configured terminal assistant. The
interfaces share the scientific engine. Reports and the offline workbench are
optional exports, not requirements for an analysis.

## What openWFN is

openWFN is a post-processing toolkit. It reads molecular and wavefunction records,
constructs a typed representation of the calculation, and exposes geometry,
topology, orbital, density, population, electrostatic-potential, export, and report
operations when the required records are present.

It does not run electronic-structure calculations or replace the program that
produced your input.
For proprietary binary `.chk` files, openWFN calls Gaussian's external `formchk`
utility when that program is installed. It reads formatted `.fchk` files directly.

## Choose your starting point

- New to the software: complete [Your first analysis](first-analysis.md).
- New to wavefunction analysis: keep [Core terminology](terminology.md) open while learning.
- Working toward a specific goal: use the [Learning paths](learning-paths.md).
- Looking up exact syntax: open the [CLI reference](../cli.md) or [Python API](../python-api.md).
- Assessing research suitability: read [Validation](../validation.md) and [Limitations](../limitations.md).

## A single scientific core

An input file is parsed once into a calculation model. Analysis services consume
that model and return typed results. CLI presentation, Python code, and reports
format those results without changing their scientific meaning. The optional
workbench visualizes selected results but is not a numerical reference.

This boundary matters for reproducibility: a distance calculated through Python and
the same distance requested from the CLI use the same coordinates, unit conversion,
indexing rules, and geometry service.

## What to install

openWFN requires Python 3.10 or newer. Start with the [Installation guide](../installation.md),
then run the first analysis below.

[Continue to your first analysis](first-analysis.md)
