# Reproduce the README examples

The README figures use the packaged water FCHK fixture and openWFN 0.13.0.
They show actual output from this fixture, not a benchmark for other systems.

## Input provenance

The input is an exact copy of `examples/water/water.fchk`. Its authoritative
history, known metadata and redistribution terms are in
[example provenance](https://github.com/sha786muhammed/openWFN/blob/main/examples/PROVENANCE.md).

SHA-256: `f3c6cb5e1f9f205e49b439339bb0833160f56be68f40e1c1097db3f30f52dcf2`.
Historical generation details that were not recorded remain unknown.
The FCHK file does not establish source convergence.

## Run the analysis

```bash
openwfn examples install ./openwfn-examples
openwfn ./openwfn-examples/water.fchk summary
openwfn ./openwfn-examples/water.fchk orbitals frontier --spin all
openwfn --format json ./openwfn-examples/water.fchk orbitals frontier --spin all
openwfn ./openwfn-examples/water.fchk plot frontier water-frontier.png
openwfn ./openwfn-examples/water.fchk workbench water-workbench.html --open
```

The orbital gap is a difference between orbital eigenvalues; it is not an
optical excitation energy. The plot is the direct PNG export, without edited
values or relabelled results. The terminal illustration is captured stdout,
line-wrapped and typeset for readability; it is not a screenshot of the guided
interface. Its source-convergence caveat is retained.

## Regenerate the committed figures

From a source checkout with the development dependencies installed:

```bash
python -m pip install -e '.[test,docs]'
python scripts/render_readme_examples.py
python scripts/check_docs.py --root .
```

Pillow is supplied through the plotting dependencies. A DejaVu Sans Mono font
is used when available, with Pillow's default font as fallback. Font and
plotting-library versions can change image appearance without changing the
scientific results.

The generator retains the [captured transcript](../assets/data/readme-examples/water-frontier-cli.txt)
and [complete JSON result](../assets/data/readme-examples/water-frontier.json),
and updates the image checksums in the asset-provenance manifest. The JSON
retains the relative input path, input checksum and actual result diagnostics;
timing and dependency versions can vary between runs.

See [the workbench guide](../workbench.md) for supported interface scope and
the [validation record](../science/validation-status.md) for method-specific
evidence. No validation status is promoted by these presentation examples.
