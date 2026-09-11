# Your first analysis

This walkthrough installs openWFN, checks the version, analyzes a water calculation,
and creates a portable offline workbench.

## Prerequisites

- Python 3.10 or newer
- A terminal
- A Gaussian formatted-checkpoint file (`.fchk`)

The repository includes a redistributable water fixture under
`examples/water/water.fchk`. If you installed from PyPI, substitute the path to your
own formatted checkpoint.

## 1. Install openWFN

```bash
python -m pip install --upgrade openwfn
openwfn --version
```

Expected version output for this handbook:

```text
openWFN 0.7.0
```

Use `python -m pip` so installation and execution refer to the same Python
environment.

## 2. Read the molecular summary

From a repository checkout:

```bash
openwfn examples/water/water.fchk summary
```

The public water fixture produces:

```text
Molecular Summary
-----------------
Formula:    H2O
Atoms:      3
Charge:     0
Spin Mult:  1
COM (Å):    (-0.000, 0.000, 0.050)
Energy:      -75.58595975 a.u.
Bonds:      2
Fragments:  1
```

The center of mass is reported in ångströms and energy in atomic units. Bond count
comes from openWFN's covalent-radius perception; it is not a bond-order assignment.

## 3. Measure the molecular geometry

CLI atom indices are one-based:

```bash
openwfn examples/water/water.fchk geometry distance 1 2
openwfn examples/water/water.fchk geometry angle 2 1 3
```

Confirm atom ordering from the source calculation or the guided interactive atom table before measuring
an unfamiliar system.

## 4. Create an offline workbench

```bash
openwfn examples/water/water.fchk workbench water-workbench.html --open
```

The HTML file is self-contained. It can be opened without a local server and does
not upload the calculation. Treat the file as research data if it contains results
you would not otherwise share.

## 5. Record reproducibility information

Record the input-file checksum, openWFN version, command, parameters, and capability
status. The report workflow automates this record:

```bash
openwfn examples/water/water.fchk report build water-report.html
```

## Troubleshooting

- `command not found`: activate the environment where you installed openWFN or run
  `python -m pip show openwfn` to locate it.
- missing record: the selected analysis needs a record absent from this input file.
- `.chk` conversion failure: install Gaussian's `formchk` or provide an `.fchk` file.
- browser does not open: open the generated HTML file manually; generation may still
  have succeeded.

## Next steps

- Choose a [learning path](learning-paths.md).
- Learn the [core terminology](terminology.md).
- Review [validation evidence](../validation.md) before research use.
