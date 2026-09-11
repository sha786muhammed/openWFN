# Tutorial: build a reproducible analysis package

The goal is not merely a pretty report. It is an evidence package another researcher can inspect and rerun.

## 1. Record identity

```bash
openwfn --version
shasum -a 256 examples/water/water.fchk
openwfn examples/water/water.fchk doctor
```

Also record the electronic-structure program, method, basis set, charge, multiplicity, and source.

## 2. Create machine-readable results

```bash
openwfn --format json --output water-summary.json \
  examples/water/water.fchk summary
openwfn examples/water/water.fchk export frontier water-frontier.csv
openwfn examples/water/water.fchk export mulliken water-mulliken.csv
```

## 3. Build the narrative report

```bash
openwfn examples/water/water.fchk report build water-report.html \
  --analyses summary,frontier,mulliken,lowdin
```

Use `--report-format markdown` and a `.md` path for version-controlled text.

## 4. Add visuals when useful

```bash
openwfn examples/water/water.fchk workbench water-workbench.html
openwfn examples/water/water.fchk plot frontier water-frontier.png --dpi 300
```

Review formula, state, ordering, status, and supported analyses. Inspect artifacts for confidential data and machine-specific metadata. Keep CSV/JSON records: neither a workbench nor screenshot should be the only numerical evidence.

For multiple inputs, follow [Batch analysis and reports](../guides/batch-and-reports.md).
