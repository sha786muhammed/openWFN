import numpy as np
import pytest

from openwfn.analysis.density import density_matrix_for_kind, evaluate_density
from openwfn.analysis.grids import molecular_grid_points
from openwfn.model import (
    Atom,
    BasisSet,
    BasisShell,
    CalculationData,
    CalculationMetadata,
    DensityMatrix,
    Molecule,
)
from openwfn.services import density_grid


def _small_density_fixture() -> CalculationData:
    molecule = Molecule(
        (
            Atom(1, (0.0, 0.0, 0.0)),
            Atom(1, (0.74, 0.0, 0.0)),
        ),
        0,
        1,
        CalculationMetadata("fixture"),
    )
    basis = BasisSet(
        (
            BasisShell(0, 0, (1.0,), (1.0,)),
            BasisShell(1, 0, (1.0,), (1.0,)),
        )
    )
    density = DensityMatrix(((1.0, 0.1), (0.1, 1.0)), "total", source="scf")
    return CalculationData(molecule=molecule, basis=basis, total_density=density)


def test_chunked_density_grid_matches_monolithic_evaluation() -> None:
    data = _small_density_fixture()
    spacing = 0.6
    padding = 1.2
    points, _, _ = molecular_grid_points(
        data.molecule,
        spacing_bohr=spacing,
        padding_bohr=padding,
    )
    matrix = density_matrix_for_kind(data, "total")
    assert data.basis is not None
    expected = evaluate_density(data.molecule, data.basis, matrix, points)

    for chunk_size in (1, 7, 65536):
        grid = density_grid(data, "total", spacing, padding, chunk_size=chunk_size)
        np.testing.assert_allclose(np.asarray(grid.values), expected, rtol=0.0, atol=1e-12)


def test_density_grid_rejects_nonpositive_chunk_size() -> None:
    data = _small_density_fixture()

    with pytest.raises(ValueError, match="chunk size must be positive"):
        density_grid(data, "total", 0.6, 1.2, chunk_size=0)
