from dataclasses import replace
from pathlib import Path

from openwfn.parsers.gaussian.fchk import parse_fchk
from openwfn.services import electrostatic_potential_point

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / "examples" / "water" / "water.fchk"


def _post_hf_water():
    data = parse_fchk(WATER)
    metadata = replace(data.molecule.metadata, method="MP2")
    molecule = replace(data.molecule, metadata=metadata)
    return replace(data, molecule=molecule)


def test_post_hf_charge_model_esp_names_scf_density_and_warns() -> None:
    data = _post_hf_water()

    result = electrostatic_potential_point(
        data,
        (3.0, 0.0, 0.0),
        "mulliken",
        1.0,
        1.0,
    )

    assert result.data["density_source"] == "scf"
    assert any("SCF density" in warning for warning in result.warnings)


def test_post_hf_grid_esp_names_scf_density_and_warns() -> None:
    data = _post_hf_water()

    result = electrostatic_potential_point(
        data,
        (3.0, 0.0, 0.0),
        "electronic",
        1.0,
        1.0,
    )

    assert result.data["density_source"] == "scf"
    assert any("SCF density" in warning for warning in result.warnings)
