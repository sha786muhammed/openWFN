# Installation

openWFN requires Python 3.10–3.13.

!!! note "Current release"

    This handbook documents openWFN 0.9.2. See the
    [0.9.2 release notes](releases/0.9.2.md) for support boundaries.

## Optional features

In your environment, install only the optional features you need:

```bash
python -m pip install "openwfn[interop,outputs,mcp]==0.9.2"
openwfn --version
```

The extras enable IOData ingestion, source-reported output extraction, and
local MCP respectively. MCP and QC output extraction remain Experimental.

## Stable release

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --upgrade openwfn
openwfn --version
```

On Windows, activate with `.venv\Scripts\activate`.

## Exact release

Pin the exact release when reproducing research:

```bash
python -m pip install openwfn==0.9.2
```

For reproducing work created with the immediately previous stable release, use:

```bash
python -m pip install openwfn==0.8.2
```

For older work created with openWFN 0.8.0, use:

```bash
python -m pip install openwfn==0.8.0
```

## Conda

```bash
conda create -n openwfn python=3.12
conda activate openwfn
python -m pip install --upgrade openwfn
```

Binary `.chk` conversion requires Gaussian's licensed `formchk` program on `PATH`. FCHK files do not require Gaussian.
