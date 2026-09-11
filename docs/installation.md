# Installation

openWFN requires Python 3.10–3.13.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install openwfn
openwfn --version
```

On Windows, activate with `.venv\Scripts\activate`.

## Conda

```bash
conda create -n openwfn python=3.12
conda activate openwfn
python -m pip install openwfn
```

Binary `.chk` conversion requires Gaussian's licensed `formchk` program on `PATH`. FCHK files do not require Gaussian.
