from pathlib import Path

import numpy as np

from openwfn.analysis.density import evaluate_density
from openwfn.parsers.gaussian.fchk import parse_fchk


def test_water_density_integrates_to_electron_count_within_half_percent() -> None:
    source = Path(__file__).resolve().parents[2] / "examples" / "water" / "water.fchk"
    data = parse_fchk(source)
    assert data.basis is not None
    assert data.total_density is not None
    axis = np.arange(-6.0, 6.0001, 0.15)
    x_grid, y_grid, z_grid = np.meshgrid(axis, axis, axis, indexing="ij")
    points = np.column_stack((x_grid.ravel(), y_grid.ravel(), z_grid.ravel()))

    density = evaluate_density(data.molecule, data.basis, data.total_density, points)
    electron_count = float(density.sum() * 0.15**3)

    assert abs(electron_count - 10.0) / 10.0 < 0.005
