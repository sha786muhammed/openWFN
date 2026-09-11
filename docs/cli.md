# CLI reference

Global flags must precede the input file:

```text
openwfn [--format table|plain|json|csv] [--output PATH] [--overwrite] FILE COMMAND
```

Core command groups are `summary`, `info`, `geometry`, `bonds`, `graph`, `orbitals`, `density`, `esp`, `population`, `view`, `workbench`, and `report`. Run `openwfn --help` or `openwfn FILE COMMAND --help` for the authoritative options.

Examples:

```bash
openwfn --format json water.fchk orbitals frontier
openwfn water.fchk population lowdin
openwfn water.fchk esp point 5 0 0 --component total
openwfn water.fchk density integrate --kind total --spacing 0.15 --padding 6
```

Exit codes distinguish invalid options (2), parsing failures (3), unavailable data (4), validation failures (5), and missing external programs (6).
