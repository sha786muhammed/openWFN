from pathlib import Path

import pytest

import openwfn

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / "examples" / "water" / "water.fchk"


def test_python_api_exports_signed_density_nci_cube(tmp_path: Path) -> None:
    calculation = openwfn.load(WATER)
    output = tmp_path / "signed-density.cube"

    result = calculation.nci_cube(
        output,
        field="signed_density",
        spacing_bohr=1.0,
        padding_bohr=2.0,
        chunk_size=None,
    )

    assert result.status == "success"
    assert result.kind == "nci_cube"
    assert result.validation_status == "Experimental"
    assert result.data["field"] == "signed_density"
    assert output.is_file()
    assert result.provenance["input_sha256"] == calculation.molecule.provenance.sha256


def test_python_api_requires_rdg_cap(tmp_path: Path) -> None:
    calculation = openwfn.load(WATER)
    with pytest.raises(ValueError, match="rdg_cap"):
        calculation.nci_cube(
            tmp_path / "rdg.cube",
            field="rdg",
            spacing_bohr=1.0,
            padding_bohr=2.0,
        )


def test_python_api_rejects_rdg_cap_for_non_rdg_field(tmp_path: Path) -> None:
    calculation = openwfn.load(WATER)
    with pytest.raises(ValueError, match="rdg_cap"):
        calculation.nci_cube(
            tmp_path / "rho.cube",
            field="rho",
            spacing_bohr=1.0,
            padding_bohr=2.0,
            rdg_cap=2.0,
        )


def test_python_api_nci_cube_honors_overwrite(tmp_path: Path) -> None:
    calculation = openwfn.load(WATER)
    output = tmp_path / "lambda2.cube"

    calculation.nci_cube(
        output,
        field="lambda2",
        spacing_bohr=1.0,
        padding_bohr=2.0,
    )
    with pytest.raises(FileExistsError):
        calculation.nci_cube(
            output,
            field="lambda2",
            spacing_bohr=1.0,
            padding_bohr=2.0,
        )

    result = calculation.nci_cube(
        output,
        field="lambda2",
        spacing_bohr=1.0,
        padding_bohr=2.0,
        overwrite=True,
    )
    assert result.status == "success"
