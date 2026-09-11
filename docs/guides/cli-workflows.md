# Command-line workflows

The general grammar is:

```text
openwfn [GLOBAL OPTIONS] FILE COMMAND [COMMAND OPTIONS]
```

Global options appear before the file. Start by checking the version, file metadata, and available records:

```bash
openwfn --version
openwfn water.fchk summary
openwfn water.fchk doctor
```

## Geometry and topology

Atom indices are one-based in the CLI.

```bash
openwfn water.fchk geometry distance 1 2
openwfn water.fchk geometry angle 2 1 3
openwfn molecule.fchk geometry dihedral 1 2 3 4
openwfn molecule.fchk bonds
openwfn molecule.fchk graph
```

The short `dist`, `angle`, and `dihedral` commands remain available for compatibility; new scripts should use the nested `geometry` interface.

## Electronic structure

```bash
openwfn molecule.fchk orbitals frontier
openwfn molecule.fchk orbitals frontier --spin beta
openwfn molecule.fchk population mulliken
openwfn molecule.fchk population lowdin
openwfn molecule.fchk density integrate --kind total
openwfn molecule.fchk esp point 0.0 0.0 3.0 --component nuclear
```

## Structured output

```bash
openwfn --format json molecule.fchk orbitals frontier
openwfn --format csv --output charges.csv molecule.fchk population mulliken
openwfn --plain --no-color molecule.fchk summary
```

Use `--quiet` for reduced output, `--verbose` or `--debug` for diagnosis, and `--overwrite` only when replacement is intentional. See the [complete CLI reference](../reference/cli.md).

