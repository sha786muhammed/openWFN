# Runtime, RAM and output validation

Use these checks to measure runtime, observed RAM use and output size.
They do not establish density convergence or scientific accuracy.
The initial implementation was checked before 0.10.0rc1 without changing
model schemas, result schemas or scientific validation labels.

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

If operating-system permissions prevent process inspection, the supervisor
terminates the owned command and reports `measurement_unavailable`. It does
not claim that memory monitoring succeeded. Use an environment that permits
process inspection for the resource benchmark.

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

Ten workflows run for each of the eleven existing real Molden wavefunctions:
summary, Mayer, Hirshfeld, DOS, PDOS, density cube, HOMO cube, workbench, electronic point ESP,
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

### Density integration memory comparison

Density integration evaluates regular-grid coordinates and density in bounded
blocks. It retains the running integral, not a complete point grid or scalar
field. The grid safety limit, numerical settings and conservation checks remain
in effect. Density and molecular-orbital cube files also evaluate and serialize
bounded blocks without retaining a complete field.
NCI cube exports use the same streamed writer, retaining their original field
diagnostics. APIs returning a grid and
workbench previews still need stored field values, but generate coordinates in
blocks. NCI grid generation uses bounded coordinate blocks as well. These paths
are not all constant-memory: returned arrays and HTML field strings still
occupy memory.

Cube publication remains atomic. A failed evaluation, interrupted stream or
write failure removes the temporary file and preserves an existing target.
Point ordering, six-value cube rows, source coefficients and field settings
are unchanged.

Parallel batches use a conservative scheduling estimate: reserve one quarter
of measured available RAM and estimate at least 512 MiB per worker, increasing
that estimate for larger input files. Common Linux cgroup memory ceilings are
respected. If memory cannot be measured, use one worker; installing the existing
`resources` extra enables the optional psutil measurement. The manifest and CLI
record requested/effective worker counts and any reduction warning. This is not
a hard memory quota or proof that an arbitrary input fits in RAM. The default
remains one worker, and resumed numerical records are unchanged.

Run the comparison on the repository's water, ethanol and biphenyl inputs:

```bash
python scripts/benchmark_density_integration.py --output density-memory.json
```

Each input runs in fresh processes with one numerical-library thread, once
through the materialized-grid reference path and once through streaming
integration. The report preserves input checksums, settings, electron counts,
statuses, runtime and peak process RSS. Only the JSON report is saved; no cubes
or HTML are generated. Choose a new filename for each run.

Peak RSS includes input loading and native libraries. The dependency-free
benchmark reports memory on macOS and Linux; on Windows it reports memory as
unavailable. Same-engine agreement checks the optimization, not independent
scientific accuracy. The default grid is a performance comparison, not a
convergence recommendation.

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
