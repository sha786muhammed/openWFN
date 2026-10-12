# Installation

Use Python 3.10–3.13 and a separate environment. This keeps openWFN's
dependencies separate from your other projects.

## Use a separate environment

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --upgrade openwfn
openwfn --version
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`; in Command
Prompt, use `.venv\Scripts\activate.bat`. With Conda, create an environment
with a supported Python version, activate it, then use its `python -m pip`.

If Linux reports that `ensurepip` is unavailable, install your distribution's
matching Python venv package or use a Conda environment.

For development from source, replace the package-install command with:

```bash
python -m pip install -e .
```

The normal installation includes file readers, output-property extraction,
local MCP and terminal chat. You do not need separate extras for these features.
Older `interop`, `outputs` and `mcp` install commands still work.

## What installation does not supply

A chat model is needed for general conversation, not for file analysis. Use
`openwfn chat` and `/connect` for setup guidance. No weights are downloaded and
no model calls are made by installation. See [Scientific assistant](assistant.md) or
[MCP setup](mcp.md).

Gaussian binary `.chk` conversion needs licensed Gaussian `formchk` on
`PATH`. Formatted `.fchk` files do not need Gaussian. File support and
analysis availability are different; check `openwfn FILE capabilities`.

## Check with packaged examples

```bash
openwfn examples install ./openwfn-examples
openwfn ./openwfn-examples/water.fchk summary
```

The install command also copies the eleven-molecule everyday-QC corpus to
`openwfn-examples/everyday-qc/`. It does not replace existing files unless
you explicitly permit overwrite.

## Reproducing an older analysis

Use the exact version recorded with that work. For the current published release:

```bash
python -m pip install openwfn==0.13.0
```

Older release pins and their support boundaries are retained in
[release history](project/release-history.md), rather than mixed into this setup guide.

Optional trusted-process monitoring is available with the `resources` extra.
It records runtime/resource evidence; it is not an OS quota or a change to
scientific validation status.
