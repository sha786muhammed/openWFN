# Your first analysis

Install openWFN, open a packaged example, and save your first result.
This walkthrough uses water. The same steps apply to other supported files
when they contain the data needed for the analysis.

## Prerequisites

- Python 3.10–3.13
- A terminal

## 1. Install openWFN

```bash
python -m pip install --upgrade openwfn
openwfn --version
```

Use `python -m pip` so installation and execution refer to the same Python
environment. Record the installed version when reproducing an analysis.

## 2. Copy the packaged examples

The package includes a water example and an eleven-molecule Molden collection.
Copy them into the current directory; no repository download is needed:

```bash
openwfn examples install ./openwfn-examples
```

The command refuses to replace an existing fixture unless you pass
`--overwrite`.

## 3. Read the molecular summary

```bash
openwfn ./openwfn-examples/water.fchk summary
```

Check the formula, atom count, charge and multiplicity in the summary.
Energy and other fields appear when the file contains them. Use `--format json`
to read the complete result in a script.

To try a different format, open the packaged ethanol example:

```bash
openwfn ./openwfn-examples/everyday-qc/ethanol.molden summary
```

For guided mode in an interactive terminal, use the same file with `open`
instead of `summary`. Scripts should use direct commands or `analyze`.

The center of mass is reported in ångströms and energy in hartree. Bond count comes from openWFN's covalent-radius perception; it is not a bond-order assignment.

## 4. Measure the molecular geometry

CLI atom indices are one-based:

```bash
openwfn ./openwfn-examples/water.fchk geometry distance 1 2
openwfn ./openwfn-examples/water.fchk geometry angle 2 1 3
```

Confirm atom ordering from the source calculation or the guided interactive atom table before measuring
an unfamiliar system.

## 5. Save a machine-readable result

```bash
openwfn --format json --output water-summary.json \
  ./openwfn-examples/water.fchk summary
```

JSON keeps the complete result: values, units, warnings, validation status
and source information. Use it in scripts or keep it with your research notes.

## 6. Record reproducibility information

Keep the input checksum, openWFN version, command and settings with your results.
You can also create a report to read or share:

```bash
openwfn ./openwfn-examples/water.fchk report build water-report.html
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
- Review [validation evidence](../science/validation-status.md) before research use.
