# Runtime, RAM and output validation

This development stage preserves openWFN 0.9.2 package/model versions and all
scientific validation labels. Resource success does not imply density-grid
convergence or validate an unimplemented scientific method.

## Scope and controls

The optional `resources` extra adds a supervisor for trusted local workflows.
The scientific engines remain shared by CLI, Python, batch, reports and MCP.
The supervisor is not exposed by MCP and is not an adversarial sandbox.

| Control | Behavior |
| --- | --- |
| Runtime | Explicit wall-clock deadline; terminate the root process group and observed descendants |
| RAM | Sample root/observed-descendant RSS and stop on an exceeded budget |
| Output | Count regular workspace files and spooled stdout/stderr; check after exit too |
| Storage | Reject before execution if free filesystem space is below the output budget |
| Parent exit | Live observed descendants produce a process error and are terminated |
| File safety | Preserve existing logs; cube publication occurs only after a complete write |
| Grids | Existing two-million-point limit checked before coordinate allocation |
| AO temporaries | Conservative 128 MiB point-array estimate accounts for Cartesian/pure expansion and long primitive contractions |

RSS and disk budgets are sampled monitors, not OS hard quotas. Short-lived
peaks, unobserved detached children and between-poll output growth can escape
sampling. Other processes can consume free disk after preflight. Workspace
symlinks are not counted as external output; commands that write elsewhere are
outside this monitor's scope. The default 10 ms polling interval is recorded.
OS isolation is required for untrusted commands.

## Reproduce the real molecular benchmark

From a development checkout, install `pip install -e ".[resources,interop]"`,
then run:

```bash
python scripts/benchmark_resources.py --output resource-report.json
```

Nine workflows run for each of the eleven existing real Molden wavefunctions:
summary, Mayer, DOS, PDOS, density cube, HOMO cube, workbench, electronic point ESP,
and HTML report. Numerical-library threads are fixed to one. Each command has
120 s, 1024 MiB observed-RSS and 128 MiB workspace-output budgets by default.
CLI options control those budgets. Density/MO cubes deliberately use 0.5 bohr
spacing and 3 bohr padding for this resource test; their scientific convergence
warnings remain meaningful.

The JSON includes source/input hashes, artifact sizes/hashes, wall time, peak
observed RSS, sample count and the reason for any resource failure. Output
artifacts use a disposable temporary directory; the JSON report is retained.
GitHub Actions runs the safety regressions on Linux, macOS and Windows and
uploads the Linux eleven-molecule resource report as an artifact.

## Preliminary local evidence

Before the execution-service outage, the completed measurement checkpoint had
99/99 commands within their resource budgets: largest observed RSS about
98 MiB; largest per-command output about 4.34 MiB. Timings are machine-specific.
The separate 1,953,125-point coordinate-allocation probe preserved the coordinate
SHA-256 while reducing observed peak RSS from about 154 to 109 MiB. That probe
includes NumPy and digest-temporary overhead; it is not a full density benchmark.

The completed full-suite checkpoint had 812 passing tests and four skips.
Later focused tests passed for descendant cleanup, disk preflight, log
preservation, streamed cube output, exact ij ordering and primitive-aware chunk
sizes. The final uploaded tree must pass CI independently; these preliminary
counts do not substitute for that check.

## Release acceptance and remaining scientific gates

Call the tested resource behavior supported only after the final head passes
the resource matrix, existing numerical/format/interface tests, browser,
documentation and security workflows. Keep failures explicit and preserve
partial scientific results. Do not infer universal peak-memory bounds or
all-device browser support.

Hirshfeld reference densities, spectroscopy, genuine transition-data NTOs and
advanced topology/basin analyses retain their independent implementation and
scientific-validation gates. The unfinished local density-derivative work is
not part of this resource stage. No new scientific label or release is
automatically promoted by a passing benchmark.
