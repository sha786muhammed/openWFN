from pathlib import Path

import pytest

import openwfn

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / "examples" / "water" / "water.fchk"


def test_fchk_load_returns_interop_container_without_breaking_convenience_api() -> None:
    calculation = openwfn.load(WATER)

    assert isinstance(calculation.data, openwfn.OpenWFNData)
    assert calculation.data.molecule is calculation.molecule
    assert calculation.orbitals().status == "success"
    assert calculation.analyze("summary").status == "success"


def test_structure_only_load_exposes_capabilities_and_safe_unsupported_result(
    tmp_path: Path,
) -> None:
    source = tmp_path / "water.xyz"
    source.write_text("3\nwater\nO 0 0 0\nH 0.7586 0 0.5043\nH -0.7586 0 0.5043\n", encoding="utf-8")

    calculation = openwfn.load(source)
    capabilities = calculation.capabilities()
    frontier = calculation.orbitals()

    assert capabilities["structure"].state == "available"
    assert capabilities["alpha_orbitals"].state == "missing"
    assert frontier.status == "failed"
    assert frontier.validation_status == "Unsupported"
    assert frontier.error is not None
    assert frontier.error.category == "DataUnavailableError"


def test_invalid_direct_api_parameters_still_raise_value_error() -> None:
    calculation = openwfn.load(WATER)

    with pytest.raises(ValueError, match="spin must be"):
        calculation.orbitals("invalid")
