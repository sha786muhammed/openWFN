# Batch analysis and reports

## Batch summaries

Batch mode applies the supported operation to multiple inputs and writes a manifest recording success or error per file.

```bash
openwfn first.fchk batch second.fchk third.fchk \
  --operation summary --workers 2 --output-dir batch-results
```

Add `--fail-fast` when the first failed input should stop the run. Without it, independent inputs continue and the manifest shows partial success. Use a conservative worker count when files are large.

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

