# Your first analysis

This walkthrough installs openWFN, checks the version, analyzes a water calculation,
and creates machine-readable and portable research records.

## Prerequisites

- Python 3.10 or newer
- A terminal

## 1. Install openWFN

```bash
python -m pip install --upgrade openwfn
openwfn --version
```

Expected version output for this handbook:

```text
openWFN 0.8.2
```

Use `python -m pip` so installation and execution refer to the same Python
environment.

## 2. Install the maintained example

The wheel includes a redistributable water formatted-checkpoint fixture. Copy it
into the current directory without cloning the repository:

```bash
openwfn examples install ./openwfn-examples
```

The command refuses to replace an existing fixture unless you pass
`--overwrite`.

## 3. Read the molecular summary

```bash
openwfn ./openwfn-examples/water.fchk summary
```

The public water fixture produces a molecular summary including the formula, atom count, charge, multiplicity, center of mass, energy, bond count, fragments, and status. Field presentation can vary by output mode; use `--format json` for machine-readable results.

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

The JSON result includes the analysis identity, units, validation status, warnings,
and provenance fields needed by downstream programs.

## 6. Record reproducibility information

Record the input-file checksum, openWFN version, command, parameters, and capability
status. The supported report workflow creates a portable human-readable record:

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
- Review [validation evidence](../validation.md) before research use.
