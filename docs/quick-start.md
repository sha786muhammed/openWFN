# Quick start

Install openWFN, copy the packaged examples, and read a summary as JSON:

```bash
python -m pip install --upgrade openwfn
openwfn examples install ./openwfn-examples
openwfn --format json ./openwfn-examples/water.fchk summary
```

Confirm that the result reports formula `H2O`, charge `0`, multiplicity `1`, and
status `success`. Follow [your first analysis](start/first-analysis.md) to measure
geometry and save results. For orbitals, populations and density checks, use
the [orbitals and density tutorial](tutorials/orbitals-density.md).

Global flags precede the input path. CLI atom indices are one-based. Keep the
input checksum and exact openWFN version with research results.
