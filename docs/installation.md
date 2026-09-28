# Installation

openWFN requires Python 3.10–3.13.

!!! warning "Pre-release handbook"

    This handbook documents openWFN 0.8.0a2. The plain package command installs
    the current stable release, which may not include commands introduced in 0.8.

## Stable release

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --upgrade openwfn
openwfn --version
```

On Windows, activate with `.venv\Scripts\activate`.

## Current pre-release

Install the newest alpha:

```bash
python -m pip install --pre --upgrade openwfn
```

After 0.8.0a2 is published, pin it when reproducing research:

```bash
python -m pip install openwfn==0.8.0a2
```

## Conda

```bash
conda create -n openwfn python=3.12
conda activate openwfn
python -m pip install --pre --upgrade openwfn
```

Binary `.chk` conversion requires Gaussian's licensed `formchk` program on `PATH`. FCHK files do not require Gaussian.
