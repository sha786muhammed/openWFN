# Scientific assistant

Ask about an open file, or connect a model for a general scientific conversation.
File-backed values come from openWFN, with units and warnings. General
explanations come from your model and may contain mistakes.

Terminal chat and MCP are included in the normal installation. openWFN does
not train or download a model for you.

## Questions about a file

Ask short questions such as “What is the HOMO energy?”, “What is the charge?”
or “What is the HOMO–LUMO gap?”. These supported questions call openWFN
locally without waiting for a model. The common `HUMO` typo is recognized
in these short requests. Orbital energies use the all-channel record: restricted
files need no alpha/beta clarification, while unrestricted files retain both channels.
This routing does not guess offset orbitals such as HOMO−1 or interpret arbitrary prose.
These supported short file questions do not require a model connection.

The same local path accepts phrases such as “HUMO value” and “HOMO value of the
FCHK”. IR, Raman and vibration requests check file capabilities without a model;
missing records produce a specific explanation rather than a request for a
population method. IR requires frequencies and IR intensities, while Raman
requires frequencies and Raman activities.

If asked to choose a population method or density operation, reply with that
choice. A new explicit request replaces the pending question. Invalid replies
do not start unrelated calculations. Ctrl+C, file/model switches and `/clear` discard pending choices while
keeping earlier scientific records. Model plans that contradict a selected
channel, method, orbital or point are rejected before calculation.

Greetings and reviewed FCHK-format help work without a model. Product help is
separate from general, unverified scientific explanations. Compact orbital
answers retain the FCHK convergence caveat; successful analysis does not establish
source convergence.

Use `/details` for the last result's diagnostic fields and source provenance,
or `/record` for its complete JSON record. Routine status labels are kept out of
short answers, but partial results, source caveats and warnings remain visible.

Other questions use the configured model. A short waiting message goes to stderr, not
machine-readable stdout. Response timeouts are reported as timeouts, separately
from connection failures; no scientific result is fabricated when planning fails.

General model explanations appear as text arrives, with a label stating that no
calculation was run. Ctrl+C stops the request. Interrupted, truncated or failed
explanations are not added to conversation history. Scientific tool plans and
JSON result records are still validated completely before use; they are not
displayed as a stream of provisional values.

Common file questions bypass the model. General chat speed depends on your
model, hardware and whether the runner has already loaded the model. A smaller
model may respond faster but give less reliable explanations. Use `/model` to
choose an installed model; openWFN does not change your selection automatically.

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

With openWFN installed and your runner started, select a model already
available on your machine. For example, with a local Ollama server:

```bash
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
- `/details`: show diagnostic fields, validation status and provenance.
- `/save`: confirm the destination for a JSON export.
- `/open PATH`: inspect and select another file; reset file-specific context.
- `/close`: close the selected file and continue general conversation.
- `/connect`: choose a connection; the old connection is retained if a switch fails.
- `/models`: search and select an available model on the current connection.
- `/model`: the short form of `/models`; connect if no model is active.
- `/disconnect`: drop the model connection without stopping its runner or deleting files.
- `/clear`: clear conversation context, keeping the file, connection and scientific records.
- `/help` or `/quit`: show help or leave the conversation.

You can also ask one question and obtain a machine-readable record:

```bash
openwfn --format json molecule.molden chat --model qwen3:8b \
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

## Density settings, resource limits and privacy

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
These checks protect scientific tool execution. General model explanations
can still contain mistakes. An orbital gap is not an optical excitation energy; successful execution is not
proof of source convergence or independent scientific validation.

External chat hosts can use the [MCP interface](mcp.md). They control their own
generated explanations, so the same guarantees about rendered terminal answers
do not extend to every external model's prose.
