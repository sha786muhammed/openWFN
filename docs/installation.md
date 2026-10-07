# Installation

openWFN supports Python 3.10–3.13.

## Use a separate environment

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --upgrade openwfn
openwfn --version
```

On Windows, activate with `.venv\Scripts\activate`. With Conda, create an
environment with a supported Python version, then use its `python -m pip`.

For development from source, replace the package-install command with:

```bash
python -m pip install -e .
```

The normal installation includes format readers, output extraction, local MCP and
terminal chat in the base installation. Existing `interop`, `outputs` and
`mcp` extra names remain accepted for compatibility.

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
python -m pip install openwfn==0.12.0
```

Older release pins and their support boundaries are retained in
[release history](project/release-history.md), rather than mixed into this setup guide.

Optional trusted-process monitoring is available with the `resources` extra.
It records runtime/resource evidence; it is not an OS quota or a change to
scientific validation status.
