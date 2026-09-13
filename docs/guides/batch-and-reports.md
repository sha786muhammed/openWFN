# Batch analysis and reports

## Batch analyses

Batch mode applies one or more registered analyses to multiple inputs and writes
a versioned manifest. Each input record contains its SHA-256 checksum, overall
status, and complete result envelopes in the requested order.

```bash
openwfn first.fchk batch second.fchk third.fchk \
  --analyses summary,frontier,mulliken \
  --workers 2 --output-dir batch-results
```

An input is `success` when every analysis succeeds, `partial` when some analyses
are unavailable, and `error` when parsing fails or every analysis fails. Invalid
analysis names are rejected before output is created. Add `--fail-fast` when the
first erroneous input should stop the run. The older `--operation summary` form
remains supported.

## Research reports

```bash
openwfn molecule.fchk report build report.html \
  --analyses summary,frontier,mulliken,lowdin
```

Set `--report-format markdown` for a Markdown artifact. Requested analyses require their underlying FCHK records; run `doctor` first if the file's contents are unknown.

## Portable workbench

```bash
openwfn molecule.fchk workbench molecule-workbench.html --open
```

The output is a standalone local HTML file. It supports review and sharing without a web service, but it contains molecular data from the input. Treat it with the same confidentiality as the source calculation.

## Suggested archive

Archive the input checksum, version, command log, batch manifest, machine-readable tables, and report together. Do not use the visual workbench as the only scientific record.
