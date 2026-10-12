# Try the supported input families

Run these from the repository root. The small format fixtures are constructed
parser examples, not independent reference calculations. Their checksums,
origins and expected capabilities are in
[the format manifest](../../validation/interop/manifest.json).

| Input | Example file |
| --- | --- |
| FCHK; FCH alias | `examples/water/water.fchk` |
| Molden; Molden.input alias | `examples/everyday-qc/ethanol.molden` |
| WFN | `tests/fixtures/interop/wfn/water.wfn` |
| WFX | `tests/fixtures/interop/wfx/water.wfx` |
| MWFN | `tests/fixtures/interop/mwfn/water.mwfn` |
| MKL | `tests/fixtures/interop/molekel/water.mkl` |
| CUBE; CUB alias | `tests/fixtures/interop/cube/water.cube` |
| XYZ | `examples/ammonia/ammonia.xyz` |
| PDB | `tests/fixtures/interop/pdb/water.pdb` |
| MOL/SDF | `tests/fixtures/interop/sdf/water.sdf` |
| Gaussian/ORCA/Q-Chem outputs | [Download the pinned larger outputs](spectroscopy/README.md) |

For example:

```bash
openwfn tests/fixtures/interop/wfn/water.wfn capabilities
openwfn tests/fixtures/interop/wfx/water.wfx open
openwfn tests/fixtures/interop/mwfn/water.mwfn orbitals frontier --spin all
openwfn tests/fixtures/interop/molekel/water.mkl population mulliken
openwfn tests/fixtures/interop/cube/water.cube open
openwfn tests/fixtures/interop/pdb/water.pdb geometry distance 1 2
```

Binary CHK needs Gaussian's separately installed `formchk`; openWFN cannot
bundle that utility or reconstruct a checkpoint without it. The input route
must give a clear conversion requirement when the utility is missing.

The complete pinned inventory also includes structure, periodic-field and
integral formats. Check all 25 format contracts with:

```bash
python scripts/run_interop_validation.py
python scripts/review_workflows.py --output /tmp/openwfn-format-properties.json
```

For a broader upstream corpus, including ghost atoms, ECPs, high-angular-momentum
and larger systems:

```bash
python scripts/review_workflows.py --iodata-corpus \
  --output /tmp/openwfn-upstream-properties.json
```

The upstream corpus includes deliberately malformed files and multi-record
inputs. A nonzero exit code means inspect the report, not automatically that
every case is broken. Single-record readers reject trajectories or collections;
provide one structure. Resource guards and unsupported method scopes must not
be bypassed to make the report look successful.
