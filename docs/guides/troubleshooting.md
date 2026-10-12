# Troubleshooting

Find the message that matches your problem below. Start with the version and
file checks so you can tell an installation problem from missing input data.

## Start with diagnostics

```bash
openwfn --version
openwfn molecule.molden doctor
openwfn --debug molecule.molden summary
```

## “Input file is required”

For a file analysis, put the path before the command:
`openwfn molecule.molden summary`. Commands such as `openwfn chat`,
`openwfn examples install DESTINATION`, `openwfn batch DIRECTORY` and
`openwfn --version` do not need a preceding input file.

## A capability is unavailable

Your file may not contain the required basis, orbital, density or spectroscopy
records. Run `openwfn FILE capabilities`. Export a suitable file from the
calculation program; changing the filename cannot supply missing data.

## `formchk` was not found

Only Gaussian supplies `formchk`. Add the Gaussian utilities to `PATH`, run `formchk input.chk output.fchk` in an authorized Gaussian environment, or obtain an `.fchk` file.

## An output already exists

Choose a new path, or put the global `--overwrite` option before the input
path after confirming that replacement is safe.

## Density integration is slow or inaccurate

Finer spacing and larger padding increase the work. Try a coarser grid for
exploration, then test convergence before reporting values. Diffuse systems
may need larger padding. If the grid exceeds the safety limit, increase
spacing or reduce padding deliberately; reducing padding can omit density tails.

## The HTML workbench does not open

Generate it without `--open`, locate the reported file, and open that file in a modern browser. No localhost server is required.

## Getting help

Capture the openWFN version, operating system, sanitized command, traceback from `--debug`, and a minimal non-confidential reproducer. Never post private checkpoint data or credentials publicly. See [Security](../project/security.md).
