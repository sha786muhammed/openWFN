# qc-iodata parser-reference procedure

This procedure uses `qc-iodata==1.0.1` as an independent FCHK parser. It is a
benchmark-only dependency and is not installed with openWFN.

## Environment

Create an isolated environment on the validation host:

```bash
conda create --prefix /tmp/openwfn-reference-python python=3.10 pip -y
conda run --prefix /tmp/openwfn-reference-python \
  python -m pip install qc-iodata==1.0.1
```

Record the host operating system, environment package list, source repository commit,
and every input SHA-256 before capture.

## Capture

From an openWFN source checkout:

```bash
conda run --prefix /tmp/openwfn-reference-python \
  python scripts/capture_qc_iodata.py INPUT.fchk reference.json
```

The command records the independently parsed energy, charge, multiplicity, atomic
numbers, coordinates in bohr, alpha/beta orbital energies and occupations, program
version, and input checksum. It refuses to replace an existing reference unless
`--overwrite` is explicitly supplied.

## Review

Before activating a manifest case, confirm that the captured checksum matches the
registered input, all numbers are finite, coordinate and energy units agree, orbital
spin ordering is documented, and the upstream input commit is immutable. A parser
agreement does not independently validate population or density algorithms; those
require separate Multiwfn comparisons and convergence evidence.

The manifest's parser references were captured with `qc-iodata==1.0.1`. Orbital
expectations use the highest occupied and lowest unoccupied alpha orbital selected from
the captured occupation arrays. Energy tolerances are `1e-10` hartree; orbital-energy
tolerances reflect the source file's printed precision (`1e-9` hartree per orbital and
`2e-9` hartree for a difference). The acetylene case remains pending because version
1.0.1 cannot parse an adjacent pair of exponent-form values in that producer's FCHK.
