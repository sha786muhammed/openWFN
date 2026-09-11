# Troubleshooting

## Start with diagnostics

```bash
openwfn --version
openwfn molecule.fchk doctor
openwfn --debug molecule.fchk summary
```

## “Input file is required”

The file normally precedes the command: `openwfn molecule.fchk summary`. The exception is `openwfn --version`, which needs no file.

## A capability is unavailable

The FCHK may not contain basis, orbital, or density records. Run `doctor`. Recreate the formatted checkpoint from a suitable calculation rather than inventing missing data.

## `formchk` was not found

Only Gaussian supplies `formchk`. Add the Gaussian utilities to `PATH`, run `formchk input.chk output.fchk` in an authorized Gaussian environment, or obtain an `.fchk` file.

## An output already exists

Choose a new path or add `--overwrite` after confirming replacement is safe.

## Density integration is slow or inaccurate

Grid cost increases rapidly as spacing decreases or padding increases. Begin with defaults, then perform a convergence study. Very diffuse systems may require larger padding.

## The HTML workbench does not open

Generate it without `--open`, locate the reported file, and open that file in a modern browser. No localhost server is required.

## Getting help

Capture the openWFN version, operating system, sanitized command, traceback from `--debug`, and a minimal non-confidential reproducer. Never post private checkpoint data or credentials publicly. See [Security](../project/security.md).

