from pathlib import Path

import openwfn
from openwfn.analysis.atom_quadrature import AtomQuadratureSettings
from openwfn.analysis.qtaim_basins import QTAIMBasinSettings

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / "examples" / "water" / "water.fchk"


def _settings() -> QTAIMBasinSettings:
    return QTAIMBasinSettings(
        quadrature=AtomQuadratureSettings(
            radial_points=2,
            theta_points=2,
            phi_points=4,
            radial_extent_bohr=1.5,
            chunk_size=16,
        ),
        max_flow_steps=1,
    )


def test_qtaim_basins_python_convenience_matches_named_analysis() -> None:
    calculation = openwfn.load(WATER)
    settings = _settings()

    convenience = calculation.qtaim_basins(settings=settings)
    named = calculation.analyze("qtaim-basins", settings=settings)

    assert convenience.kind == "qtaim_basins"
    assert convenience.status == named.status
    assert convenience.validation_status == named.validation_status == "Experimental"
    assert convenience.data["settings"] == named.data["settings"]
    assert convenience.data["atoms"] == named.data["atoms"]


def test_qtaim_basins_api_preserves_experimental_status_and_provenance() -> None:
    calculation = openwfn.load(WATER)

    result = calculation.qtaim_basins(settings=_settings())

    assert result.validation_status == "Experimental"
    assert result.provenance["input_sha256"] == calculation.molecule.provenance.sha256
    assert result.data["boundary_diagnostics"]["status"] == "not_requested"
