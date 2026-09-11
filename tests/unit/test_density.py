import math

import numpy as np
import pytest

from openwfn.analysis.density import density_matrix_for_kind, evaluate_density, integrate_density
from openwfn.constants import BOHR_TO_ANGSTROM
from openwfn.model import (
    Atom,
    BasisSet,
    BasisShell,
    CalculationData,
    CalculationMetadata,
    DensityMatrix,
    Molecule,
    VolumetricGrid,
)


def test_density_contracts_ao_matrix_on_both_indices() -> None:
    molecule = Molecule((Atom(1, (0.0, 0.0, 0.0)),), 0, 2, CalculationMetadata("fixture"))
    basis = BasisSet((BasisShell(0, 0, (1.0,), (1.0,)),))
    matrix = DensityMatrix(((1.0,),), "total")

    density = evaluate_density(molecule, basis, matrix, np.zeros((1, 3)))

    expected = (2.0 / math.pi) ** 1.5
    assert density[0] == pytest.approx(expected, abs=1e-12)


def test_density_rejects_matrix_basis_size_mismatch() -> None:
    molecule = Molecule((Atom(1, (0.0, 0.0, 0.0)),), 0, 2, CalculationMetadata("fixture"))
    basis = BasisSet((BasisShell(0, 0, (1.0,), (1.0,)),))
    matrix = DensityMatrix(((1.0, 0.0), (0.0, 1.0)), "total")

    with pytest.raises(ValueError, match="density matrix size"):
        evaluate_density(molecule, basis, matrix, np.zeros((1, 3)))


def test_grid_density_integration_uses_bohr_volume() -> None:
    step = 0.5 * BOHR_TO_ANGSTROM
    grid = VolumetricGrid(
        origin=(0.0, 0.0, 0.0),
        axes=((step, 0.0, 0.0), (0.0, step, 0.0), (0.0, 0.0, step)),
        shape=(2, 2, 2),
        values=(1.0,) * 8,
        value_unit="electron/bohr^3",
    )

    result = integrate_density(grid, expected_electrons=1.0)

    assert result.electron_count == pytest.approx(1.0)
    assert result.relative_error == pytest.approx(0.0)


def test_density_channels_are_derived_from_total_and_spin_matrices() -> None:
    molecule = Molecule((Atom(1, (0.0, 0.0, 0.0)),), 0, 2, CalculationMetadata("fixture"))
    data = CalculationData(
        molecule=molecule,
        total_density=DensityMatrix(((1.5, 0.2), (0.2, 0.5)), "total"),
        spin_density=DensityMatrix(((0.5, 0.0), (0.0, -0.5)), "spin"),
    )

    alpha = density_matrix_for_kind(data, "alpha")
    beta = density_matrix_for_kind(data, "beta")

    np.testing.assert_allclose(alpha.values, ((1.0, 0.1), (0.1, 0.0)), atol=1e-12)
    np.testing.assert_allclose(beta.values, ((0.5, 0.1), (0.1, 0.5)), atol=1e-12)
    assert density_matrix_for_kind(data, "total") is data.total_density
    assert density_matrix_for_kind(data, "spin") is data.spin_density


def test_density_channel_requires_available_source_matrices() -> None:
    molecule = Molecule((Atom(1, (0.0, 0.0, 0.0)),), 0, 2, CalculationMetadata("fixture"))

    with pytest.raises(Exception, match="Spin density matrix"):
        density_matrix_for_kind(
            CalculationData(
                molecule=molecule,
                total_density=DensityMatrix(((1.0,),), "total"),
            ),
            "alpha",
        )
