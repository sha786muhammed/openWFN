# Local MCP preview

This Experimental adapter in openWFN 0.9.1 lets an MCP client request selected openWFN analyses.
It runs locally over stdio and reads files inside one configured directory.
It does not provide a public HTTP service, upload endpoint, or authentication.

## Install

Use a separate environment, then install the optional features:

```bash
python -m pip install "openwfn[mcp,interop,outputs]==0.9.1"
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

The supported registry currently includes `summary`, `frontier`, `beta-frontier`,
`frontier-all`, `mulliken`, and `lowdin`. Availability depends on the file's data.
Geometry measurements, density grids, ESP, exports, and batch execution are not
exposed by this initial adapter. They remain available through existing interfaces.

For a wavefunction input, inspect it first and request only an available analysis.
For a QC output log, use `output_properties` directly; it does not construct a
complete wavefunction. See [output properties](output-properties.md) for the
distinction between source-reported and recomputed properties.

## Results and failures

Scientific results use the existing `ResultRecord` envelope. Keep the `status`,
`units`, `warnings`, and `provenance` when reporting results. `partial` means
incomplete data, and `failed` is not a valid scientific answer. Analyses cannot
recover properties absent from a file.

Invalid paths and inputs larger than the configured limit produce MCP tool
errors. Parsing and analysis failures return structured records with
`status: "failed"`; clients must check this field even when the protocol call
itself succeeds.

## Limits

The adapter does not write output files or execute shell commands. Symlinks
resolving outside the data root are rejected. The default per-file limit is
100 MiB; `--max-file-bytes` changes it. This is an input-size check, not a bound
on parser memory or analysis runtime.

Use a dedicated input directory that untrusted processes cannot modify while
the server runs. This local preview is not a sandbox for hostile files and
has no CPU, memory, or execution-time isolation. Results include source paths;
consider that before sharing them with an external client. Remote deployment
needs separate access-control, upload, and resource-limit work.
