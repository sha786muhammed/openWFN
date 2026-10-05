from types import SimpleNamespace

import numpy as np

from openwfn.data import OpenWFNData, SourceMetadata
from openwfn.ingest import _augment_cclib_vibrations
from openwfn.vibrational import VibrationalRecord


def test_frequency_only_cclib_output_creates_minimal_vibrational_calculation(monkeypatch, tmp_path) -> None:
    source = tmp_path / "water_freq.out"
    source.write_text("frequency output fixture\n", encoding="utf-8")
    normalized = OpenWFNData(
        calculation=None,
        structure=None,
        periodic=None,
        grids=(),
        integrals=None,
        metadata=SourceMetadata(source_program="Gaussian"),
        provenance=None,
    )
    parsed = SimpleNamespace(
        metadata={"package": "Gaussian", "package_version": "16"},
        atomnos=np.array([8, 1, 1]),
        atomcoords=np.array(
            [
                [
                    [0.0, 0.0, 0.0],
                    [0.7586, 0.0, 0.5043],
                    [-0.7586, 0.0, 0.5043],
                ]
            ]
        ),
        charge=0,
        mult=1,
        vibfreqs=np.array([1806.46, 3908.95, 3995.0]),
        vibirs=np.array([10.0, 20.0, 30.0]),
        vibdisps=np.zeros((3, 3, 3)),
    )

    monkeypatch.setattr(
        "openwfn.ingest.import_module",
        lambda name: SimpleNamespace(ccread=lambda *args, **kwargs: parsed)
        if name == "cclib.io"
        else __import__(name, fromlist=["*"]),
    )

    augmented = _augment_cclib_vibrations(normalized, source)

    assert augmented.calculation is not None
    record = augmented.calculation.records["vibrations"]
    assert isinstance(record, VibrationalRecord)
    assert [mode.frequency_cm1 for mode in record.modes] == [1806.46, 3908.95, 3995.0]
    assert augmented.calculation.molecule.charge == 0
    assert augmented.calculation.molecule.multiplicity == 1
    assert len(augmented.calculation.molecule.atoms) == 3
