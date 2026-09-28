from pathlib import Path

from openwfn.parsers.gaussian.fchk import parse_fchk
from openwfn.services import electrostatic_potential_point

ROOT = Path(__file__).resolve().parents[2]
POST_HF = ROOT / "tests" / "fixtures" / "scientific" / "post_hf_scf_density.fchk"


def test_post_hf_charge_model_esp_names_scf_density_and_warns() -> None:
    data = parse_fchk(POST_HF)

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
    data = parse_fchk(POST_HF)

    result = electrostatic_potential_point(
        data,
        (3.0, 0.0, 0.0),
        "electronic",
        1.0,
        1.0,
    )

    assert result.data["density_source"] == "scf"
    assert any("SCF density" in warning for warning in result.warnings)
