from pathlib import Path

import numpy as np
import pytest

import openwfn
from openwfn.analysis.nci import NCIFieldBatch, NCISettings


def _water_data():
    source = Path(openwfn.__file__).parent / "example_data/water.fchk"
    calculation = openwfn.load(source)
    assert calculation.data.calculation is not None
    return calculation.data.calculation


def test_nci_scalar_grids_are_finite_for_non_rdg_fields() -> None:
    from openwfn.nci_services import nci_scalar_grid

    data = _water_data()
    for field in ("rho", "lambda2", "signed_density"):
        grid, diagnostics = nci_scalar_grid(data, field, 1.0, 2.0, chunk_size=7)
        values = np.asarray(grid.values, dtype=float)
        assert len(values) > 0
        assert np.all(np.isfinite(values))
        assert diagnostics["field"] == field
        assert diagnostics["grid_points"] == len(values)
        assert diagnostics["clipped_finite_count"] == 0
        assert diagnostics["density_tail_substitution_count"] == 0


def test_nci_grid_accepts_none_chunk_size_as_bounded_default() -> None:
    from openwfn.nci_services import nci_scalar_grid

    data = _water_data()
    grid, diagnostics = nci_scalar_grid(
        data, "rdg", 1.0, 2.0, rdg_cap=1.5, chunk_size=None
    )
    assert np.all(np.isfinite(grid.values))
    assert isinstance(diagnostics["chunk_size"], int)
    assert diagnostics["chunk_size"] > 0


def test_rdg_grid_requires_explicit_positive_finite_cap() -> None:
    from openwfn.nci_services import nci_scalar_grid

    data = _water_data()
    for cap in (None, 0.0, -1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="rdg_cap"):
            nci_scalar_grid(data, "rdg", 1.0, 2.0, rdg_cap=cap)


def test_rdg_cap_is_rejected_for_non_rdg_fields() -> None:
    from openwfn.nci_services import nci_scalar_grid

    data = _water_data()
    with pytest.raises(ValueError, match="rdg_cap"):
        nci_scalar_grid(data, "rho", 1.0, 2.0, rdg_cap=2.0)


def test_rdg_grid_clips_finite_values_and_substitutes_density_tail() -> None:
    from openwfn.nci_services import nci_scalar_grid

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


def test_nci_grid_is_chunk_invariant_within_machine_precision() -> None:
    from openwfn.nci_services import nci_scalar_grid

    data = _water_data()
    grid_a, diagnostics_a = nci_scalar_grid(
        data, "rdg", 1.0, 2.0, rdg_cap=1.5, chunk_size=3
    )
    grid_b, diagnostics_b = nci_scalar_grid(
        data, "rdg", 1.0, 2.0, rdg_cap=1.5, chunk_size=101
    )
    np.testing.assert_allclose(grid_a.values, grid_b.values, rtol=1.0e-14, atol=1.0e-15)
    assert diagnostics_a["clipped_finite_count"] == diagnostics_b["clipped_finite_count"]
    assert diagnostics_a["density_tail_substitution_count"] == diagnostics_b[
        "density_tail_substitution_count"
    ]


def _bad_hessian_batch(point_count: int) -> NCIFieldBatch:
    rho = np.full(point_count, 0.2, dtype=float)
    return NCIFieldBatch(
        rho=rho,
        gradient_norm=np.full(point_count, 0.1, dtype=float),
        rdg=np.full(point_count, 0.25, dtype=float),
        hessian_eigenvalues=np.full((point_count, 3), np.nan, dtype=float),
        lambda2=np.full(point_count, np.nan, dtype=float),
        signed_density=np.full(point_count, np.nan, dtype=float),
        rdg_valid_mask=np.ones(point_count, dtype=bool),
        field_valid_mask=np.zeros(point_count, dtype=bool),
        lambda2_sign_ambiguous_mask=np.zeros(point_count, dtype=bool),
        hessian_antisymmetry_residual=np.full(point_count, 1.0, dtype=float),
        invalid_hessian_count=point_count,
    )


def test_rdg_export_ignores_bad_hessian_while_hessian_fields_reject(monkeypatch) -> None:
    import openwfn.nci_services as nci_services

    data = _water_data()

    def fake_evaluate_nci(_data, points, **_kwargs):
        return _bad_hessian_batch(len(points))

    monkeypatch.setattr(nci_services, "evaluate_nci", fake_evaluate_nci)
    rdg_grid, _ = nci_services.nci_scalar_grid(
        data, "rdg", 1.5, 1.0, rdg_cap=1.0, chunk_size=5
    )
    np.testing.assert_allclose(rdg_grid.values, 0.25)

    with pytest.raises(ValueError, match="lambda2"):
        nci_services.nci_scalar_grid(data, "lambda2", 1.5, 1.0, chunk_size=5)
    with pytest.raises(ValueError, match="signed-density"):
        nci_services.nci_scalar_grid(data, "signed_density", 1.5, 1.0, chunk_size=5)


def test_rho_export_does_not_use_hessian_nci_path(monkeypatch) -> None:
    import openwfn.nci_services as nci_services

    data = _water_data()

    def forbidden_nci(*_args, **_kwargs):
        raise AssertionError("rho export must not evaluate NCI Hessian fields")

    monkeypatch.setattr(nci_services, "evaluate_nci", forbidden_nci)
    grid, _ = nci_services.nci_scalar_grid(data, "rho", 1.5, 1.0, chunk_size=5)
    assert np.all(np.isfinite(grid.values))


def test_rdg_invalid_outside_density_tail_aborts_and_cube_is_not_published(
    monkeypatch, tmp_path: Path
) -> None:
    import openwfn.nci_services as nci_services

    data = _water_data()

    def fake_invalid_rdg(_data, points, **_kwargs):
        count = len(points)
        return NCIFieldBatch(
            rho=np.full(count, 0.2, dtype=float),
            gradient_norm=np.full(count, 0.1, dtype=float),
            rdg=np.full(count, np.nan, dtype=float),
            hessian_eigenvalues=np.zeros((count, 3), dtype=float),
            lambda2=np.zeros(count, dtype=float),
            signed_density=np.zeros(count, dtype=float),
            rdg_valid_mask=np.zeros(count, dtype=bool),
            field_valid_mask=np.zeros(count, dtype=bool),
            lambda2_sign_ambiguous_mask=np.ones(count, dtype=bool),
            hessian_antisymmetry_residual=np.zeros(count, dtype=float),
            invalid_nonfinite_count=count,
        )

    monkeypatch.setattr(nci_services, "evaluate_nci", fake_invalid_rdg)
    output = tmp_path / "must-not-exist.cube"
    with pytest.raises(ValueError, match="outside the declared low-density tail"):
        nci_services.nci_cube_export(
            data, "rdg", 1.5, 1.0, output, False, rdg_cap=1.0, chunk_size=5
        )
    assert not output.exists()


def test_nci_grid_obeys_shared_grid_limit_before_field_evaluation(monkeypatch) -> None:
    from openwfn.analysis import grids
    from openwfn.nci_services import nci_scalar_grid

    data = _water_data()
    monkeypatch.setattr(grids, "MAX_GRID_POINTS", 2)
    with pytest.raises(ValueError, match="exceeding the configured safety limit"):
        nci_scalar_grid(data, "rho", 1.0, 2.0)


def test_nci_cube_export_writes_atomic_finite_cube_and_metadata(tmp_path: Path) -> None:
    from openwfn.nci_services import nci_cube_export

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
