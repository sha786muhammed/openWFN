# Tutorial: build a reproducible analysis package

Save a report with your input checksum, commands and numerical results so
another researcher can repeat the analysis. Start with the packaged examples:

```bash
openwfn examples install ./openwfn-examples
```

No source checkout is needed. Keep reports alongside complete JSON results.

## 1. Record identity

```bash
openwfn --version
shasum -a 256 ./openwfn-examples/water.fchk
openwfn ./openwfn-examples/water.fchk doctor
```

Also record the electronic-structure program, method, basis set, charge, multiplicity, and source.

## 2. Create machine-readable results

```bash
openwfn --format json --output water-summary.json \
  ./openwfn-examples/water.fchk summary
openwfn ./openwfn-examples/water.fchk export frontier water-frontier.csv
openwfn ./openwfn-examples/water.fchk export mulliken water-mulliken.csv
```

## 3. Build the narrative report

```bash
openwfn ./openwfn-examples/water.fchk report build water-report.html \
  --analyses summary,frontier,mulliken,lowdin
```

Use `--report-format markdown` and a `.md` path for version-controlled text.

## 4. Add visuals when useful

```bash
openwfn ./openwfn-examples/water.fchk workbench water-workbench.html
openwfn ./openwfn-examples/water.fchk plot frontier water-frontier.png --dpi 300
```

The workbench interface is Stable for the tested Chromium scope and intended for optional visual inspection. Review formula, state, ordering, status, and supported analyses. Inspect artifacts for confidential data and machine-specific metadata. Keep CSV/JSON records: neither a workbench nor screenshot should be the only numerical evidence.

For multiple inputs, follow [Batch analysis and reports](../guides/batch-and-reports.md).
