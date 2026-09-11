# Reproducible reports

```bash
openwfn water.fchk report build water-report.html --analyses summary,frontier,mulliken,lowdin
```

The self-contained report records the input checksum, openWFN version, command, parameters, units, results, validation states, and unavailable analyses. Use Markdown when a text-first artifact is preferable:

```bash
openwfn water.fchk report build water-report.md --report-format markdown
```
