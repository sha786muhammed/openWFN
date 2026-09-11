import numpy as np
import pytest

from openwfn.analysis.population import lowdin_population, mulliken_population
from openwfn.model import Atom, CalculationMetadata, DensityMatrix, Molecule


def _hydrogen_molecule() -> Molecule:
    return Molecule(
        atoms=(Atom(1, (0.0, 0.0, 0.0)), Atom(1, (0.0, 0.0, 0.74))),
        charge=0,
        multiplicity=1,
        metadata=CalculationMetadata("fixture"),
    )


def test_mulliken_population_conserves_electrons_and_charge() -> None:
    density = DensityMatrix(((1.0, 0.2), (0.2, 1.0)), "total")
    overlap = np.array(((1.0, 0.25), (0.25, 1.0)))

    result = mulliken_population(_hydrogen_molecule(), density, overlap, (0, 1))

    assert result.electron_populations == pytest.approx((1.05, 1.05))
    assert result.atomic_charges == pytest.approx((-0.05, -0.05))
    assert result.electron_count == pytest.approx(2.1)
    assert result.total_charge == pytest.approx(-0.1)
    assert result.conservation_error == pytest.approx(0.1)


def test_lowdin_population_uses_symmetric_positive_square_root() -> None:
    density = DensityMatrix(((1.0, 0.0), (0.0, 1.0)), "total")
    overlap = np.array(((1.0, 0.2), (0.2, 1.0)))

    result = lowdin_population(_hydrogen_molecule(), density, overlap, (0, 1))

    assert result.electron_populations == pytest.approx((1.0, 1.0), abs=1e-12)
    assert result.atomic_charges == pytest.approx((0.0, 0.0), abs=1e-12)
    assert result.total_charge == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize(
    ("overlap", "message"),
    [
        (np.eye(3), "density and overlap"),
        (np.array(((1.0, 2.0), (0.0, 1.0))), "symmetric"),
        (np.array(((1.0, 2.0), (2.0, 1.0))), "positive semidefinite"),
    ],
)
def test_lowdin_rejects_invalid_overlap_matrices(overlap: np.ndarray, message: str) -> None:
    density = DensityMatrix(((1.0, 0.0), (0.0, 1.0)), "total")

    with pytest.raises(ValueError, match=message):
        lowdin_population(_hydrogen_molecule(), density, overlap, (0, 1))


def test_population_rejects_invalid_ao_atom_mapping() -> None:
    density = DensityMatrix(((1.0, 0.0), (0.0, 1.0)), "total")

    with pytest.raises(ValueError, match="AO-to-atom"):
        mulliken_population(_hydrogen_molecule(), density, np.eye(2), (0, 2))
