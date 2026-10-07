# Scientific assistant

The development version includes terminal chat and MCP in the normal installation.
Chat uses an existing model to choose an openWFN tool. The engine supplies the
values, units, warnings and provenance; generated numerical prose is not shown.
No model is trained or downloaded by openWFN.

Short requests for HOMO/LUMO energy, the HOMO–LUMO gap, charge, multiplicity or
formula use a small explicit local routing vocabulary. They call the scientific
engine without waiting for a model response. The common `HUMO` typo is recognized
in these short requests. Orbital energies use the all-channel record: restricted
files need no alpha/beta clarification, while unrestricted files retain both channels.
This routing does not guess offset orbitals such as HOMO−1 or interpret arbitrary prose.
Model configuration is still required when starting chat.

Other questions use the configured model. A waiting message goes to stderr, not
machine-readable stdout. Response timeouts are reported as timeouts, separately
from connection failures; no scientific result is fabricated when planning fails.

## Start a local conversation

Install this checkout in an environment, and configure a model already available
on your machine. For a local Ollama server with an installed Qwen model:

```bash
python -m pip install -e .
openwfn molecule.molden chat --model qwen3:8b
```

That model name is an example, not a requirement. The adapter uses an
OpenAI-compatible chat-completions endpoint. The default base URL is
`http://127.0.0.1:11434/v1`. Set `OPENWFN_CHAT_MODEL` and
`OPENWFN_CHAT_ENDPOINT`, or use `--model` and `--endpoint`. Compatibility with
one configured model does not establish support for every model server.

Ask about charge/multiplicity, frontier orbital energies, MO contributions,
Mulliken/Löwdin/Hirshfeld charges, Mayer bond orders, density consistency,
vibrations, excited states, NTO or supported real-space analyses. Availability
depends on the file. For ELF/LOL/NCI and density derivatives, specify an explicit
Cartesian point in bohr. QTAIM is a bounded critical-point search, not a complete
basin integration toolkit.

For example, ask “Which atoms contribute to HOMO?” and reply “Use Löwdin,
alpha channel” if asked for a projection method. The answer reports the actual
projection convention; it does not treat those contributions as unique observables.

Commands within a conversation:

- `/inspect`: inspect the current file and available analyses.
- `/record`: show the complete last scientific result as JSON.
- `/save`: confirm the destination for a JSON export.
- `/open`: explicitly select another local file and clear previous results.
- `/help` or `/quit`: show help or leave the conversation.

You can also ask one question and obtain a machine-readable record:

```bash
openwfn --format json molecule.fchk chat --model qwen3:8b \
  --question "What is the HOMO-LUMO gap?"
```

Without model configuration, use `openwfn FILE open` for guided analysis or a
direct CLI command. Python analysis and MCP clients do not require this local
chat model.

## Numerical controls and privacy

Capabilities are inspected before a model request. File changes invalidate the
session's cached data. Model requests contain the question, bounded clarification
context and capability metadata, not raw files, AO coefficients, grids, source
paths or scientific result arrays. The complete result remains local.

Density calculations require confirmation of kind, spacing, padding and grid
size. The assistant defaults to total density, 0.3 bohr spacing and 6 bohr padding;
these settings are not a convergence guarantee. Single-question mode does not
run a grid unless you explicitly pass `--confirm-grid`. This approves the
requested settings within the assistant's resource limits, not scientific accuracy.

Default limits are 100 MiB per input, 256 AO functions for computations other
than summary, 200,000 density-grid points, 4,096 spectral samples and at most
32 centers for assistant QTAIM searches. They are application checks, not an
OS-enforced memory/time sandbox. Use the direct API for intentionally larger jobs.

Remote endpoints require HTTPS and explicit `--allow-remote` permission. If
authentication is needed, set `OPENWFN_CHAT_API_KEY` in your environment; never
put a key in a URL or repository. A loopback server can itself forward requests
to a cloud service, so configure the server for local inference if privacy matters.
openWFN makes no paid calls or public deployment automatically.

Malformed plans and network failures stop the request. The assistant does not
retry indefinitely or execute model-supplied shell commands. Missing facts stay
missing, partial results stay partial, and Experimental analyses stay Experimental.
An orbital gap is not an optical excitation energy; successful execution is not
proof of source convergence or independent scientific validation.

External chat hosts can use the [MCP interface](mcp.md). They control their own
generated explanations, so the same guarantees about rendered terminal answers
do not extend to every external model's prose.
