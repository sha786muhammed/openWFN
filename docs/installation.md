# Installation

openWFN requires Python 3.10–3.13.

!!! note "Current release"

    The stable release is 0.10.0. See the
    [0.10.0 release notes](releases/0.10.0.md) for support boundaries.

## Optional features

In your environment, install only the optional features you need:

```bash
python -m pip install "openwfn[interop,outputs,mcp]==0.10.0"
openwfn --version
```

The extras enable IOData ingestion, source-reported output extraction, and
local MCP respectively. Local MCP is Stable within its tested read-only scope; QC output extraction
remains Experimental.

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
python -m pip install openwfn==0.10.0
```

For reproducing work created with the immediately previous stable release, use:

```bash
python -m pip install openwfn==0.9.2
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

## Resource monitoring

Install `openwfn[interop,resources]==0.10.0` for everyday QC and optional
trusted-process monitoring. The `resources` extra does not change scientific
labels and does not provide OS hard quotas.

The [0.10.0rc1 candidate notes](releases/0.10.0rc1.md) are retained for
reproducing candidate-era work; 0.10.0 supersedes that candidate.
