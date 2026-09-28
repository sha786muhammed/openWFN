# Installation

openWFN requires Python 3.10–3.13.

!!! note "Current release"

    This handbook documents openWFN 0.8.1.

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
python -m pip install openwfn==0.8.1
```

## Conda

```bash
conda create -n openwfn python=3.12
conda activate openwfn
python -m pip install --upgrade openwfn
```

Binary `.chk` conversion requires Gaussian's licensed `formchk` program on `PATH`. FCHK files do not require Gaussian.
