# Scientific assistant

openWFN includes terminal chat and MCP in the normal installation.
Chat can discuss quantum chemistry without a file, or use an existing model to
choose an openWFN tool for an open file. File-backed values, units, warnings and
provenance come from the engine. General explanations are model-generated,
clearly labelled, and not independently verified.
No model is trained or downloaded by openWFN.

Short requests for HOMO/LUMO energy, the HOMO–LUMO gap, charge, multiplicity or
formula use a small explicit local routing vocabulary. They call the scientific
engine without waiting for a model response. The common `HUMO` typo is recognized
in these short requests. Orbital energies use the all-channel record: restricted
files need no alpha/beta clarification, while unrestricted files retain both channels.
This routing does not guess offset orbitals such as HOMO−1 or interpret arbitrary prose.
These supported short file questions do not require a model connection.

Other questions use the configured model. A waiting message goes to stderr, not
machine-readable stdout. Response timeouts are reported as timeouts, separately
from connection failures; no scientific result is fabricated when planning fails.

## Start a local conversation

```bash
openwfn chat
```

Start without a file or model. Use `/connect` to choose Ollama, LM Studio or an
OpenAI-compatible endpoint, then choose one of its available models. Local
inference has no per-request API charge, but hardware requirements and licences
vary. Official downloads: [Ollama](https://ollama.com/download) and
[LM Studio](https://lmstudio.ai/download). Install/start your chosen runner and
enable its local server; openWFN offers Check again if it is unavailable.
Choose and download models in the runner. openWFN does not install them for you.

Without a file, ask conceptual questions such as “Explain electron correlation”.
With a file open, start conceptual questions with “Explain”, “Define”, “Compare”,
“Why” or “How”; file-specific wording is routed to the scientific tool boundary.
Use `/close` for a general conversation without file context. This does not
make the model a validated scientific reference.

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
- `/open PATH`: inspect and select another file; reset file-specific context.
- `/close`: close the selected file and continue general conversation.
- `/connect`: choose a connection; the old connection is retained if a switch fails.
- `/models`: search and select an available model on the current connection.
- `/disconnect`: drop the model connection without stopping its runner or deleting files.
- `/clear`: clear conversation context, keeping the file, connection and scientific records.
- `/help` or `/quit`: show help or leave the conversation.

You can also ask one question and obtain a machine-readable record:

```bash
openwfn --format json molecule.fchk chat --model qwen3:8b \
  --question "What is the HOMO-LUMO gap?"
```

The last scientific record retains its original source even after closing or
replacing a file. General explanations do not replace it. `/save` confirms the
destination and overwrite choice, and writes atomically. Ctrl+C cancels the
current request and returns to the prompt; Ctrl+D exits. Enter sends and
Alt+Enter inserts a newline. History and connections are session-only.
Discovery verifies endpoint/model availability, not scientific accuracy or
successful inference for every model.

Without a model, use supported short file questions, `openwfn FILE open` for
guided analysis, or a direct CLI command. Python analysis and MCP clients do not
require a chat model. General single-question prose is available with
`openwfn chat --model MODEL --question "Explain basis sets"`. General prose has
no ResultRecord schema and is not offered as JSON/CSV or scientific file export.

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

Remote endpoints require HTTPS and explicit `--allow-remote` or `/connect`
permission after disclosure. Changing connections clears model conversation
context; existing conversation is not silently forwarded to another provider.
No automated literature search is included. References in model prose are not
verified citations. No raw file or engine-result interpretation is sent to the
conceptual model in this release. If
authentication is needed, set `OPENWFN_CHAT_API_KEY` in your environment; never
put a key in a URL or repository. A loopback server can itself forward requests
to a cloud service, so configure the server for local inference if privacy matters.
openWFN makes no paid calls or public deployment automatically.

Malformed plans and network failures stop the request. The assistant does not
retry indefinitely or execute model-supplied shell commands. Missing facts stay
missing, partial results stay partial, and Experimental analyses stay Experimental.
These safeguards apply to scientific tool execution. General model prose is
untrusted and can contain mistakes. An orbital gap is not an optical excitation energy; successful execution is not
proof of source convergence or independent scientific validation.

External chat hosts can use the [MCP interface](mcp.md). They control their own
generated explanations, so the same guarantees about rendered terminal answers
do not extend to every external model's prose.
