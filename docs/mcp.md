# Local MCP interface

openWFN 0.10.1 provides a **Stable local MCP interface** for the selected
read-only registered analyses, backed by real molecular
CLI/Python/batch/report/MCP parity checks. Individual analysis results retain
their own scientific validation status and limitations.

It runs locally over stdio and reads files inside one configured directory. It
does not provide a public HTTP service, upload endpoint, or authentication.

## Install

Use a separate environment, then install the optional features:

```bash
python -m pip install "openwfn[mcp,interop,outputs]==0.10.1"
```

The adapter is tested with MCP SDK 2.2.0. The base openWFN installation does
not require that SDK. The `interop` and `outputs` extras enable the existing
IOData and cclib readers respectively.

## Connect a client

Configure an MCP host using absolute paths to your environment and input folder:

```json
{
  "mcpServers": {
    "openwfn": {
      "command": "/absolute/environment/bin/python",
      "args": [
        "-m", "openwfn.mcp_server",
        "--data-root", "/absolute/input-folder"
      ]
    }
  }
}
```

Host configuration syntax can vary. The command starts a server that waits for
MCP messages on standard input; running it alone does not open a chat interface.
Standard output is reserved for protocol messages.

## Tools

| Tool | Purpose |
| --- | --- |
| `list_analyses` | List supported registry analyses. |
| `inspect_file(path, format_hint=None)` | Report file-specific wavefunction capabilities. |
| `run_analysis(path, analysis, format_hint=None)` | Run one registered analysis. |
| `output_properties(path)` | Extract source-reported QC output properties with cclib. |

Paths can be relative to the data root. Absolute paths must also be inside it.
Binary Gaussian `.chk` files are rejected by every file-reading MCP tool,
including when a format hint or an existing `.fchk` sidecar is provided.
Convert them outside MCP with Gaussian's `formchk`, then supply the `.fchk`
file. The existing CLI/API checkpoint workflow is unchanged.

The registry includes the established summary/frontier/population analyses plus
`orbital-composition`, `mayer`, `dos`, and `pdos`. Availability still depends on
the records actually present in the input file. File-writing cube/CSV/plot
operations, batch execution, and expensive real-space export workflows remain
outside the read-only MCP surface.

For a wavefunction input, inspect it first and request only an available analysis.
For a QC output log, use `output_properties` directly; it does not construct a
complete wavefunction. See [output properties](output-properties.md) for the
distinction between source-reported and recomputed properties.

## Results and failures

Scientific results use the existing `ResultRecord` envelope. Keep the `status`,
`units`, `warnings`, and `provenance` when reporting results. `partial` means
incomplete or conditionally valid data, and `failed` is not a valid scientific
answer. Analyses cannot recover properties absent from a file.

Invalid paths and inputs larger than the configured limit produce MCP tool
errors. Parsing and analysis failures return structured records with
`status: "failed"`; clients must check this field even when the protocol call
itself succeeds.

## Limits

The adapter does not write output files or execute shell commands. Symlinks
resolving outside the data root are rejected. The default per-file limit is
100 MiB; `--max-file-bytes` changes it. This is an input-size check, not a hard
bound on parser memory or analysis runtime.

Overlap-based analyses are limited to 256 AO functions by default before
overlap construction. Configure an intentional higher limit with
`--max-basis-functions N` or `create_server(root, max_basis_functions=N)`; this
is a resource bound, not a runtime guarantee. DOS grids are independently
limited to 100000 points and PDOS to two million output projection values.
Expensive grids/cubes/real-space methods are not exposed.

Use a dedicated input directory that untrusted processes cannot modify while
the server runs. The local interface is not an adversarial sandbox and has no
OS-enforced CPU, memory, or execution-time isolation. Results include source
paths; consider that before sharing them with an external client. Remote
deployment needs separate access-control, upload, and resource-limit work.

## Interface evidence

The common-registry parity matrix checks composition, Mayer, DOS and PDOS on
the native water FCHK plus all eleven versioned everyday-QC Molden inputs. Each
case compares full numerical data across CLI, Python, batch manifests, embedded
HTML report JSON and an in-process MCP client/server session. Existing tests
also exercise a real stdio session, malformed input, missing capabilities,
file-size/resource bounds and filesystem containment.

Stable describes this documented local interface—not universal source-program,
molecule, or method validation. Each returned analysis retains its own
scientific status, provenance, warnings, and reference boundary.
