# Quick start

Install the current pre-release, copy the packaged example, and run one
machine-readable analysis:

```bash
python -m pip install --pre --upgrade openwfn
openwfn examples install ./openwfn-examples
openwfn --format json ./openwfn-examples/water.fchk summary
```

Confirm that the result reports formula `H2O`, charge `0`, multiplicity `1`, and
status `success`. Then follow [your first analysis](start/first-analysis.md) for
doctor, frontier-orbital, population, validation, and report workflows.

Global flags precede the input path. CLI atom indices are one-based. Keep the
input checksum and exact openWFN version with research results.
