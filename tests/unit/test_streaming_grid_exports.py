"""Cube export must evaluate in blocks and publish only complete files."""

from pathlib import Path

import numpy as np
import pytest

from openwfn import orbital_services, services
from openwfn.exporters import cube
from openwfn.parsers.gaussian.fchk import parse_fchk

WATER = Path(__file__).resolve().parents[2] / "examples/water/water.fchk"


@pytest.mark.parametrize("kind", ["density", "orbital"])
def test_cube_exports_do_not_materialize_grids_and_preserve_bytes(kind, tmp_path, monkeypatch):
    data = parse_fchk(WATER)
    output = tmp_path / "field.cube"
    if kind == "density":
        expected = cube.format_cube(services.density_grid(data, "total", 0.6, 1.2), data.molecule)
        module = services
        blocked = "density_grid"
    else:
        previous = orbital_services.orbital_cube_export(
            data, "homo", "alpha", 0.6, 1.2, output, False
        )
        expected = output.read_text()
        output.unlink()
        module = orbital_services
        blocked = "orbital_grid"

    def forbid(*args, **kwargs):
        raise AssertionError("Full grid allocation during cube export")

    monkeypatch.setattr(module, blocked, forbid)
    result = (
        services.density_cube_export(data, "total", 0.6, 1.2, output, False)
        if kind == "density"
        else orbital_services.orbital_cube_export(data, "homo", "alpha", 0.6, 1.2, output, False)
    )
    assert output.read_text() == expected
    assert result.data["grid_points"] > 0
    if kind == "orbital":
        assert result.data["squared_amplitude_integral"] == pytest.approx(
            previous.data["squared_amplitude_integral"], abs=1e-12
        )


def test_chunk_writer_keeps_six_value_rows_across_block_boundaries(tmp_path):
    writer = getattr(cube, "write_cube_chunks", None)
    assert callable(writer), "A bounded field writer is required"
    data = parse_fchk(WATER)
    grid = services.density_grid(data, "total", 0.6, 1.2)
    values = np.asarray(grid.values)
    writer(
        data.molecule,
        tmp_path / "field.cube",
        origin_bohr=tuple(v / 0.529177210903 for v in grid.origin),
        shape=grid.shape,
        spacing_bohr=0.6,
        value_unit=grid.value_unit,
        chunks=(values[i : i + 7] for i in range(0, len(values), 7)),
    )
    assert (tmp_path / "field.cube").read_text() == cube.format_cube(grid, data.molecule)


@pytest.mark.parametrize("error", [OSError("disk full"), KeyboardInterrupt()])
def test_failed_field_stream_preserves_target_and_removes_temporary_files(error, tmp_path):
    writer = getattr(cube, "write_cube_chunks", None)
    assert callable(writer), "A bounded field writer is required"
    output = tmp_path / "field.cube"
    output.write_text("previous field")

    def broken():
        yield np.ones(3)
        raise error

    with pytest.raises(type(error)):
        writer(
            parse_fchk(WATER).molecule,
            output,
            origin_bohr=(0.0, 0.0, 0.0),
            shape=(2, 2, 2),
            spacing_bohr=1.0,
            value_unit="electron/bohr^3",
            chunks=broken(),
            overwrite=True,
        )
    assert output.read_text() == "previous field"
    assert list(tmp_path.iterdir()) == [output]


@pytest.mark.parametrize("kind", ["density", "orbital"])
def test_grid_returning_apis_do_not_allocate_all_coordinates(kind, monkeypatch):
    data = parse_fchk(WATER)
    module = services if kind == "density" else orbital_services

    def forbidden(*args, **kwargs):
        raise AssertionError("materialized all coordinates")

    monkeypatch.setattr(module, "molecular_grid_points", forbidden, raising=False)
    result = (
        services.density_grid(data, "total", 0.6, 1.2)
        if kind == "density"
        else orbital_services.orbital_grid(data, "homo", "alpha", 0.6, 1.2)
    )
    assert len(result.values) > 0


def test_nci_grid_uses_bounded_coordinates(monkeypatch):
    from openwfn import nci_services

    def forbidden(*args, **kwargs):
        raise AssertionError("materialized NCI coordinates")

    monkeypatch.setattr(nci_services, "molecular_grid_points", forbidden, raising=False)
    grid, diagnostics = nci_services.nci_scalar_grid(parse_fchk(WATER), "rho", 0.6, 1.2)
    assert len(grid.values) == diagnostics["grid_points"]


def test_workbench_fields_use_bounded_coordinates(monkeypatch):
    from openwfn.workbench import payload

    def forbidden(*args, **kwargs):
        raise AssertionError("materialized preview coordinates")

    monkeypatch.setattr(payload, "molecular_grid_points", forbidden, raising=False)
    result = payload.WorkbenchPayload.from_calculation(parse_fchk(WATER), include_fields=True)
    assert {field["id"] for field in result.fields} == {
        "density-total",
        "orbital-homo",
        "esp-mulliken",
    }


def test_stream_integral_overflow_does_not_publish_cube(tmp_path):
    output = tmp_path / "overflow.cube"
    with pytest.raises(ValueError, match="nonfinite"):
        cube.write_cube_chunks(
            parse_fchk(WATER).molecule,
            output,
            origin_bohr=(0.0, 0.0, 0.0),
            shape=(1, 1, 2),
            spacing_bohr=1.0,
            value_unit="electron/bohr^3",
            chunks=(np.asarray([1e308]), np.asarray([1e308])),
        )
    assert not output.exists()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("field", ["rho", "lambda2", "signed_density", "rdg"])
def test_nci_cube_stream_matches_materialized_export(field, tmp_path, monkeypatch):
    from openwfn import nci_services

    data = parse_fchk(WATER)
    output = tmp_path / "field.cube"
    kwargs = {"rdg_cap": 10.0} if field == "rdg" else {}
    grid, diagnostics = nci_services.nci_scalar_grid(data, field, .6, 1.2, **kwargs)
    expected = cube.format_cube(grid, data.molecule,
        comment=f"openWFN Experimental NCI {field}; convention={nci_services._NCI_CONVENTION_VERSION}").encode()

    def forbidden(*args, **kwargs):
        raise AssertionError("materialized NCI scalar field during export")

    monkeypatch.setattr(nci_services, "nci_scalar_grid", forbidden)
    current = nci_services.nci_cube_export(data, field, .6, 1.2, output, False, **kwargs)
    assert output.read_bytes() == expected
    for key, value in diagnostics.items():
        assert current.data[key] == value
    assert current.validation_status == "Experimental"
