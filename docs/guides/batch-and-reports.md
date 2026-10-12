# Batch analysis and reports

Batch runs default to one worker. When you request more, openWFN may reduce
parallelism using a conservative available-memory estimate. The CLI and batch
manifest show requested and effective worker counts and explain reductions.
If memory information is unavailable, it uses one worker. This scheduling
check is not a hard RAM limit; individual calculations still need suitable
settings and sufficient memory.

Use batch mode to analyse a collection of files. Save the complete results as
JSON, use the CSV summary to find problems, and create reports when needed.

## Batch analyses

Batch mode runs your chosen analyses on each file. It saves a manifest listing
each input checksum, status and complete results in the requested order.

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

Keep notes and manifests outside the input folder, or select input files
explicitly. For example, the packaged Molden collection also contains a README
and a manifest; scanning that whole folder reports those as unsupported files.
To analyse only its wavefunctions:

```bash
openwfn batch ./openwfn-examples/everyday-qc/*.molden \
  --analyses summary,frontier-all --output-dir ./results
```

Each completed run also writes `batch-summary.csv`, a compact one-row-per-input
index containing checksums, status, skip state, analysis counts, elapsed time,
and errors. Progress is written to stderr so JSON stdout stays machine-readable;
use global `--quiet` to suppress progress.

Multi-worker runs keep at most twice the effective worker count submitted at a
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
and load. Scientific accuracy is checked by the method-specific reference suites, not
this structure-only throughput benchmark.

## Research reports

```bash
openwfn molecule.molden report build report.html \
  --analyses summary,frontier,mulliken,lowdin
```

Use `--report-format markdown` to save Markdown instead of HTML. Each requested
analysis needs the relevant records, regardless of file format. Check
`capabilities` first if you do not know what the file contains.

## Optional offline workbench

```bash
openwfn molecule.molden workbench molecule-workbench.html --open
```

The output is a standalone local HTML file for visualization and teaching. It is not
a numerical reference or a substitute for structured results. It supports review and
sharing without a web service, but it contains molecular data from the input. Treat it
with the same confidentiality as the source calculation.

## Suggested archive

Archive the input checksum, version, command log, batch manifest, machine-readable tables, and report together. Do not use the visual workbench as the only scientific record.
