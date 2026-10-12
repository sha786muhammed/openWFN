# Command-line workflows

Choose a file and an analysis. For scripts, use this command pattern:

```text
openwfn [GLOBAL OPTIONS] FILE COMMAND [COMMAND OPTIONS]
```

Put global options before the file path. Start by checking the version and
the data available in your file:

```bash
openwfn --version
openwfn molecule.molden capabilities
openwfn molecule.molden summary
```

## Guided terminal

Run `openwfn FILE open` to choose an analysis without remembering commands.
The workflow is **Choose → Configure → Run → Review → Save**. Wide terminals
show file-aware navigation beside the current task; narrow terminals stack it.
Density settings show units and grid size before you approve a run. A grid that
exceeds the safety limit is rejected before allocation.

Review values and important warnings first. Use Details for diagnostics and
provenance, or save the complete JSON result. The proposed destination is shown
before writing; existing files need a separate replacement confirmation.
Missing data are not inferred: a structure file does not contain a wavefunction,
and IR/Raman need frequency and intensity/activity records.

**All calculation methods and requirements** groups the registered methods by
task, including methods unavailable from your file with their missing-record
reasons. Spectrum workflows let you choose broadening, curve range and point
count. Hirshfeld exposes quadrature resolution and extent; QTAIM exposes seeds,
iteration limits and bounded bond paths. Cancel before running to return to the
method choices. JSON keeps the full evidence; spectrum CSV contains curve
columns for plotting and does not replace the JSON record.

Direct commands remain available for scripts. Add `--compact` before the file
for a shorter human-readable result; `--verbose` shows diagnostic fields.

## Geometry and topology

Atom indices are one-based in the CLI.

```bash
openwfn water.fchk geometry distance 1 2
openwfn water.fchk geometry angle 2 1 3
openwfn molecule.molden geometry dihedral 1 2 3 4
openwfn molecule.molden bonds
openwfn molecule.molden graph
```

The short `dist`, `angle`, and `dihedral` commands remain available for compatibility; new scripts should use the nested `geometry` interface.

## Electronic structure

```bash
openwfn molecule.molden orbitals frontier
openwfn molecule.molden orbitals frontier --spin beta
openwfn molecule.molden population mulliken
openwfn molecule.molden population lowdin
openwfn molecule.molden density integrate --kind total
openwfn molecule.molden esp point 0.0 0.0 3.0 --component nuclear
```

## Structured output

```bash
openwfn --format json molecule.molden orbitals frontier
openwfn --format csv --output charges.csv molecule.molden population mulliken
openwfn --plain --no-color molecule.molden summary
```

Use `--quiet` for reduced output, `--verbose` or `--debug` for diagnosis, and `--overwrite` only when replacement is intentional. See the [complete CLI reference](../reference/cli.md).
