"""Density integration must not materialize a full point/value grid."""
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from openwfn import services
from openwfn.analysis import grids
from openwfn.analysis.density import density_matrix_for_kind, integrate_density
from openwfn.model import DensityMatrix
from openwfn.parsers.gaussian.fchk import parse_fchk
from openwfn.scientific import expected_electron_count

WATER = Path(__file__).resolve().parents[2] / "examples/water/water.fchk"


@pytest.mark.parametrize("chunk_size", [1, 7, 65536])
def test_point_blocks_preserve_full_grid_coordinates_and_order(chunk_size):
    iterator = getattr(grids, "iter_molecular_grid_chunks", None)
    assert callable(iterator), "A bounded coordinate iterator is required"
    molecule = parse_fchk(WATER).molecule
    points, _, _ = grids.molecular_grid_points(molecule, spacing_bohr=.6, padding_bohr=1.2)
    blocks = list(iterator(molecule, spacing_bohr=.6, padding_bohr=1.2, chunk_size=chunk_size))
    assert all(0 < len(block) <= chunk_size for block in blocks)
    np.testing.assert_array_equal(np.concatenate(blocks), points)


@pytest.mark.parametrize("kind", ["total", "alpha", "beta", "spin"])
def test_integration_does_not_allocate_full_grid_and_preserves_results(kind, monkeypatch):
    data = parse_fchk(WATER)
    data = replace(data, spin_density=DensityMatrix(
        tuple(tuple(0.0 for _ in row) for row in data.total_density.values),
        "spin", source="scf"))
    expected = integrate_density(services.density_grid(data, kind, .6, 1.2),
        expected_electron_count(data, kind).value)

    def forbid_full_grid(*args, **kwargs):
        raise AssertionError("integration allocated the full grid")

    monkeypatch.setattr(services, "density_grid", forbid_full_grid)
    monkeypatch.setattr(services, "molecular_grid_points", forbid_full_grid, raising=False)
    result = services.density_integration(data, kind, .6, 1.2)
    assert result.data["electron_count"] == pytest.approx(expected.electron_count, abs=1e-8)
    assert result.data["absolute_error"] == pytest.approx(expected.absolute_error, abs=1e-10)
    assert result.data["error_metric"] == expected.error_metric
    assert result.status == ("success" if expected.passed else "partial")
    assert result.data["density_source"] == density_matrix_for_kind(data, kind).source


def test_oversized_integration_rejects_before_density_evaluation(monkeypatch):
    def forbid_evaluation(*args, **kwargs):
        raise AssertionError("evaluated an unsafe grid")

    monkeypatch.setattr(services, "evaluate_density", forbid_evaluation)
    with pytest.raises(ValueError, match="safety limit"):
        services.density_integration(parse_fchk(WATER), "total", .001, 10.)


@pytest.mark.parametrize("chunk_size", [0, -1, True, 1.5])
def test_point_blocks_reject_invalid_chunk_sizes(chunk_size):
    iterator = getattr(grids, "iter_molecular_grid_chunks", None)
    assert callable(iterator), "A bounded coordinate iterator is required"
    with pytest.raises(ValueError, match="chunk size"):
        list(iterator(parse_fchk(WATER).molecule, spacing_bohr=.6,
            padding_bohr=1.2, chunk_size=chunk_size))
