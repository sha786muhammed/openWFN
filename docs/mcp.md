# Local MCP interface

openWFN provides a local, read-only MCP interface for registered analyses. The MCP adapter is an interface layer over the same analysis registry used by Python and the CLI; it does not maintain a separate scientific implementation. Individual results retain their own validation status and limitations.

It runs locally over stdio and reads files inside one configured directory. It does not provide a public HTTP/REST service, upload endpoint, or authentication layer.

## Install

Use a separate environment. The development version includes the MCP SDK and
format/output readers in the normal installation:

```bash
python -m pip install -e .
```

Published 0.11.0 installations still use the `mcp`, `interop` and `outputs`
extras. Existing extra names remain accepted for compatibility in this checkout.

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

Host configuration syntax can vary. The command starts a server that waits for MCP messages on standard input; running it alone does not open a chat interface. Standard output is reserved for protocol messages.

## Tools

| Tool | Purpose |
| --- | --- |
| `list_analyses` | List supported registry analyses. |
| `inspect_file(path, format_hint=None)` | Report file-specific capabilities. |
| `run_analysis(path, analysis, format_hint=None, parameters=None)` | Run one registered analysis with an optional validated scalar parameter mapping. |
| `output_properties(path)` | Extract source-reported QC output properties with cclib. |
| `integrate_density(path, kind, spacing_bohr, padding_bohr, confirmed=False)` | Check density after approval of the grid settings, within resource limits. |

`list_analyses` also lists accepted scalar parameter names. For a one-point
ELF/LOL/NCI or derivative calculation, pass `x_bohr`, `y_bohr`, and `z_bohr`.
`run_analysis` also accepts `stored-grid` for bounded stored-field inspection;
it does not infer that a scalar grid is an electron density.

`parameters` is a JSON object whose values are simple scalars accepted by the selected registered analysis. Nested objects/lists and non-finite numeric values are rejected rather than forwarded ambiguously. For example, an agent may request:

```json
{
  "path": "water_freq.log",
  "analysis": "ir-spectrum",
  "parameters": {
    "fwhm_cm1": 20.0,
    "points": 1001
  }
}
```

or one normal mode:

```json
{
  "path": "water_freq.log",
  "analysis": "normal-mode",
  "parameters": {
    "mode": 2
  }
}
```

Paths can be relative to the data root. Absolute paths must also remain inside it. Binary Gaussian `.chk` files are rejected by every file-reading MCP tool. Convert them outside MCP with Gaussian's `formchk`, then provide the `.fchk` file.

## Registered spectroscopy analyses

The same registry now exposes these **Experimental** vibrational analyses when the input contains the necessary typed records:

| Analysis | MCP data |
|---|---|
| `vibrations` | Source mode table and capability flags |
| `ir-spectrum` | Source IR sticks plus broadened arrays |
| `raman-spectrum` | Source Raman-activity sticks plus broadened activity arrays |
| `normal-mode` | One mode's source metadata and Cartesian displacement vectors |

The MCP server returns structured numerical data, not a plot. A client may visualize those arrays, but the returned `ResultRecord` remains the scientific record.

Gaussian Raman values are returned as **Raman activities**, not experimental Raman intensities. openWFN does not infer laser frequency, temperature, or other assumptions required for an activity-to-intensity conversion. Imaginary modes remain signed in source data and are excluded from broadened physical spectra with an explicit warning.

For a vibrational input, `inspect_file` can be used first to confirm available spectroscopy capabilities. Missing IR/Raman/vector records remain unavailable; the MCP layer does not synthesize them.

## Results and failures

Scientific results use the existing `ResultRecord` envelope. Preserve `status`, `validation_status`, `units`, `warnings`, and `provenance` when communicating results. `partial` means incomplete or conditionally valid data, and `failed` is not a scientific answer.

The MCP result for a given analysis/parameter set is parity-tested against the Python registry result. This establishes interface consistency, not independent scientific validation of every method or source-program variant.

Invalid paths and inputs larger than the configured limit produce MCP tool errors. Parsing and analysis failures return structured records with `status: "failed"`; clients must check this field even when the protocol call itself succeeds.

## Limits and security boundary

The adapter does not write output files or execute shell commands. Symlinks resolving outside the data root are rejected. The default per-file limit is 100 MiB; `--max-file-bytes` changes it. This is an input-size check, not a hard bound on parser memory or analysis runtime.

Computations other than summary are limited to 256 AO functions by default.
Configure an intentional higher limit with `--max-basis-functions N` or
`create_server(root, max_basis_functions=N)`. Density grids are limited to
200,000 points by default (`--max-grid-points`); spectra to 4,096 samples.
QTAIM is limited to 32 centers. File-writing plots/cubes/reports, batch execution,
and Workbench generation remain outside the read-only MCP surface.

Use a dedicated input directory that untrusted processes cannot modify while the server runs. The local interface is not an adversarial sandbox and has no OS-enforced CPU, memory, or execution-time isolation. Results include source paths; consider that before sharing them with an external client. Remote deployment requires separate access control, upload validation, authentication, and resource isolation.

## Interface evidence

The existing MCP suite exercises path containment, malformed input, missing capabilities, resource limits, real stdio sessions, and registered-analysis parity. Vibrational parity additionally checks parameter forwarding and equality of scientific data, units, warnings, validation status, and provenance with the Python API.

Stable describes the documented **local interface**, not universal scientific validation. The new vibrational analyses remain Experimental pending independent validation evidence. See [Vibrational spectroscopy](science/vibrational-spectroscopy.md) for scientific semantics and boundaries.
