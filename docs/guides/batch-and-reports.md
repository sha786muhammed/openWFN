# Batch analysis and reports

## Batch analyses

Batch mode applies one or more registered analyses to multiple inputs and writes
a versioned manifest. Each input record contains its SHA-256 checksum, overall
status, and complete result envelopes in the requested order.

```bash
openwfn first.fchk batch second.fchk third.fchk \
  --analyses summary,frontier,mulliken \
  --workers 2 --resume --output-dir batch-results
```

An input is `success` when every analysis succeeds, `partial` when some analyses
are unavailable or a structure-only summary is returned, and `error` when parsing fails or every analysis fails. Invalid
analysis names are rejected before output is created. Add `--fail-fast` when the
first erroneous input should stop the run. The older `--operation summary` form
remains supported.

`--resume` reuses a per-input result only when its input checksum and batch
configuration fingerprint match. Successful and partial records are reusable;
error records are retried. Changing the requested analyses or input contents
invalidates the corresponding cache. Both per-input records in `records/` and
`batch-manifest.json` are replaced atomically so interruption cannot leave a
partially written JSON document.
The fingerprint includes openWFN, parser-backend, model, result, batch, and
requested-analysis versions, plus effective format hints. A version or hint
change recomputes the record.

Files and directories can be mixed. Add `--recursive` to scan subdirectories;
registered parser suffixes are selected in stable order, duplicates are removed,
and the output directory is excluded automatically. Preview discovery without
performing analysis or requiring an output directory:

```bash
openwfn batch calculations/ --recursive --dry-run \
  --analyses summary,frontier
```

For mixed ambiguous files, place a JSON map outside the scanned directory:

```json
{
  "calculations/water.dat": "gamess",
  "calculations/structure.qcschema.json": "json_qcschema"
}
```

Map keys are relative to the map file. Run
`openwfn batch calculations/ --format-map formats.json --output-dir results/`.
For one homogeneous batch, `openwfn --input-format FORMAT_ID batch ...` is
shorter. Unknown IDs, missing map targets, and conflicting hints stop before
analysis records are written.

Top-level `success` and `partial` batches exit 0; `failed` batches exit
nonzero. Any parse/analysis error or unsupported discovered file makes the
batch failed. An all-unsupported directory still writes a manifest. Inspect
`unsupported_details` for paths, reasons, and readable checksums. For
`--fail-fast`, `attempted_count` and `stopped_early` distinguish the attempted
subset from all discovered files. Successful per-file analyses remain in the
manifest even when another input fails.

Each completed run also writes `batch-summary.csv`, a compact one-row-per-input
index containing checksums, status, skip state, analysis counts, elapsed time,
and errors. Progress is written to stderr so JSON stdout stays machine-readable;
use global `--quiet` to suppress progress.

Multi-worker runs keep at most twice the requested worker count submitted at a
time. Results are written as workers finish, so a slow early input does not delay
persistence of later completed inputs. The final manifest and CSV index still
use deterministic input order.

## Throughput benchmark

The repository benchmark stages deterministic XYZ inputs and runs real parsing,
partial structure-summary analysis, and result writing. Choose a count that fits the machine and
record its hardware and load; for example:

```bash
python scripts/benchmark_batch.py \
  --count 1000 \
  --workers "$(nproc)" \
  --workspace /tmp/openwfn-benchmark \
  --output openwfn-benchmark.json
```

The output records counts, elapsed time, files per second, parent-process peak
Python memory, and software versions. Compare timing only on equivalent hardware
and load. Scientific FCHK accuracy remains covered by the validation suite, not
this structure-only orchestration benchmark.

## Research reports

```bash
openwfn molecule.fchk report build report.html \
  --analyses summary,frontier,mulliken,lowdin
```

Set `--report-format markdown` for a Markdown artifact. Requested analyses require their underlying FCHK records; run `doctor` first if the file's contents are unknown.

## Optional offline workbench

```bash
openwfn molecule.fchk workbench molecule-workbench.html --open
```

The output is a standalone local HTML file for visualization and teaching. It is not
a numerical reference or a substitute for structured results. It supports review and
sharing without a web service, but it contains molecular data from the input. Treat it
with the same confidentiality as the source calculation.

## Suggested archive

Archive the input checksum, version, command log, batch manifest, machine-readable tables, and report together. Do not use the visual workbench as the only scientific record.
