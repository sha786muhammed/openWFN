# Your first analysis

This walkthrough installs openWFN, checks the version, analyzes a water calculation,
and creates machine-readable and portable research records.

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
openWFN 0.8.0a1
```

Use `python -m pip` so installation and execution refer to the same Python
environment.

## 2. Read the molecular summary

From a repository checkout:

```bash
openwfn examples/water/water.fchk summary
```

The public water fixture produces a molecular summary including the formula, atom count, charge, multiplicity, center of mass, energy, bond count, fragments, and status. Field presentation can vary by output mode; use `--format json` for machine-readable results.

The center of mass is reported in ångströms and energy in hartree. Bond count comes from openWFN's covalent-radius perception; it is not a bond-order assignment.

## 3. Measure the molecular geometry

CLI atom indices are one-based:

```bash
openwfn examples/water/water.fchk geometry distance 1 2
openwfn examples/water/water.fchk geometry angle 2 1 3
```

Confirm atom ordering from the source calculation or the guided interactive atom table before measuring
an unfamiliar system.

## 4. Save a machine-readable result

```bash
openwfn --format json --output water-summary.json \
  examples/water/water.fchk summary
```

The JSON result includes the analysis identity, units, validation status, warnings,
and provenance fields needed by downstream programs.

## 5. Record reproducibility information

Record the input-file checksum, openWFN version, command, parameters, and capability
status. The supported report workflow creates a portable human-readable record:

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
