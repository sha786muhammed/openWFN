from pathlib import Path

import numpy as np
import pytest

import openwfn
from openwfn.analysis.nci import NCISettings


def _water_data():
    source = Path(openwfn.__file__).parent / "example_data/water.fchk"
    calculation = openwfn.load(source)
    assert calculation.data.calculation is not None
    return calculation.data.calculation


def test_nci_scalar_grids_are_finite_for_non_rdg_fields() -> None:
    from openwfn.services import nci_scalar_grid

    data = _water_data()
    for field in ("rho", "lambda2", "signed_density"):
        grid, diagnostics = nci_scalar_grid(
            data, field, 1.0, 2.0, chunk_size=7
        )
        values = np.asarray(grid.values, dtype=float)
        assert len(values) > 0
        assert np.all(np.isfinite(values))
        assert diagnostics["field"] == field
        assert diagnostics["grid_points"] == len(values)
        assert diagnostics["clipped_finite_count"] == 0
        assert diagnostics["density_tail_substitution_count"] == 0


def test_rdg_grid_requires_explicit_positive_finite_cap() -> None:
    from openwfn.services import nci_scalar_grid

    data = _water_data()
    for cap in (None, 0.0, -1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="rdg_cap"):
            nci_scalar_grid(data, "rdg", 1.0, 2.0, rdg_cap=cap)


def test_rdg_cap_is_rejected_for_non_rdg_fields() -> None:
    from openwfn.services import nci_scalar_grid

    data = _water_data()
    with pytest.raises(ValueError, match="rdg_cap"):
        nci_scalar_grid(data, "rho", 1.0, 2.0, rdg_cap=2.0)


def test_rdg_grid_clips_finite_values_and_substitutes_density_tail() -> None:
    from openwfn.services import nci_scalar_grid

    data = _water_data()
    settings = NCISettings(density_floor=0.05)
    grid, diagnostics = nci_scalar_grid(
        data,
        "rdg",
        0.8,
        3.0,
        settings=settings,
        rdg_cap=0.4,
        chunk_size=11,
    )
    values = np.asarray(grid.values, dtype=float)
    assert np.all(np.isfinite(values))
    assert np.all(values <= 0.4)
    assert diagnostics["density_tail_substitution_count"] > 0
    assert diagnostics["clipped_finite_count"] > 0
    assert diagnostics["rdg_cap"] == 0.4
    assert diagnostics["density_floor"] == 0.05


def test_nci_grid_is_chunk_invariant() -> None:
    from openwfn.services import nci_scalar_grid

    data = _water_data()
    grid_a, diagnostics_a = nci_scalar_grid(
        data, "rdg", 1.0, 2.0, rdg_cap=1.5, chunk_size=3
    )
    grid_b, diagnostics_b = nci_scalar_grid(
        data, "rdg", 1.0, 2.0, rdg_cap=1.5, chunk_size=101
    )
    np.testing.assert_allclose(grid_a.values, grid_b.values, rtol=0.0, atol=0.0)
    assert diagnostics_a["clipped_finite_count"] == diagnostics_b["clipped_finite_count"]
    assert diagnostics_a["density_tail_substitution_count"] == diagnostics_b[
        "density_tail_substitution_count"
    ]


def test_nci_grid_obeys_shared_grid_limit_before_field_evaluation(monkeypatch) -> None:
    from openwfn.analysis import grids
    from openwfn.services import nci_scalar_grid

    data = _water_data()
    monkeypatch.setattr(grids, "MAX_GRID_POINTS", 2)
    with pytest.raises(ValueError, match="exceeding the configured safety limit"):
        nci_scalar_grid(data, "rho", 1.0, 2.0)


def test_nci_cube_export_writes_atomic_finite_cube_and_metadata(tmp_path: Path) -> None:
    from openwfn.services import nci_cube_export

    data = _water_data()
    output = tmp_path / "water-nci.cube"
    result = nci_cube_export(
        data,
        "rdg",
        1.0,
        2.0,
        output,
        False,
        rdg_cap=2.0,
        chunk_size=13,
    )
    assert result.status == "success"
    assert result.validation_status == "Experimental"
    assert output.exists()
    text = output.read_text(encoding="utf-8").lower()
    assert "nan" not in text
    assert "inf" not in text
    assert result.data["field"] == "rdg"
    assert result.data["rdg_cap"] == 2.0
    assert result.data["grid_points"] > 0
    assert result.data["density_source"] is not None
    assert result.units["spacing"] == "bohr"
    assert result.units["padding"] == "bohr"
