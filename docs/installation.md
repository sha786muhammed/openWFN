# Installation

openWFN requires Python 3.10–3.13.

!!! note "Current release"

    This handbook follows the source checkout, including unreleased 0.9.0
    features. The last published release documented here is 0.8.2. See the
    [0.9.0 preparation notes](releases/0.9.0.md) before using source-only commands.

## Unreleased source checkout

From the repository checkout, use a separate environment and install:

```bash
python -m pip install -e ".[interop,outputs,mcp]"
openwfn --version
```

The source version is 0.9.0; this is not evidence of a PyPI release. Choose only
the extras you need. MCP and QC output extraction remain Experimental.

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
python -m pip install openwfn==0.8.2
```

For reproducing work created with the immediately previous stable release, use:

```bash
python -m pip install openwfn==0.8.1
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
