import numpy as np
import pytest

from openwfn.analysis.electrostatics import (
    electronic_esp_from_grid,
    nuclear_esp,
    point_charge_esp,
    total_esp_from_grid,
)
from openwfn.constants import BOHR_TO_ANGSTROM
from openwfn.model import Atom, CalculationMetadata, Molecule, VolumetricGrid


def _h2() -> Molecule:
    return Molecule(
        atoms=(
            Atom(1, (0.0, 0.0, 0.0)),
            Atom(1, (2.0 * BOHR_TO_ANGSTROM, 0.0, 0.0)),
        ),
        charge=0,
        multiplicity=1,
        metadata=CalculationMetadata("fixture"),
    )


def test_nuclear_esp_sums_nuclear_charge_over_distance() -> None:
    values = nuclear_esp(_h2(), np.array(((1.0, 0.0, 0.0),)))

    assert values == pytest.approx((2.0,))


def test_nuclear_esp_masks_points_at_nuclei() -> None:
    values = nuclear_esp(_h2(), np.array(((0.0, 0.0, 0.0),)))

    assert np.isnan(values[0])


def test_point_charge_esp_far_field_approaches_total_charge_over_r() -> None:
    centers = np.array(((-0.5, 0.0, 0.0), (0.5, 0.0, 0.0)))
    charges = np.array((0.4, 0.6))
    distance = 1_000_000.0

    value = point_charge_esp(centers, charges, np.array(((distance, 0.0, 0.0),)))[0]

    assert value * distance == pytest.approx(1.0, rel=1e-5)


def test_point_charge_esp_validates_shapes() -> None:
    with pytest.raises(ValueError, match="centers"):
        point_charge_esp(np.ones((2, 2)), np.ones(2), np.ones((1, 3)))
    with pytest.raises(ValueError, match="one charge"):
        point_charge_esp(np.ones((2, 3)), np.ones(3), np.ones((1, 3)))
    with pytest.raises(ValueError, match="points"):
        point_charge_esp(np.ones((2, 3)), np.ones(2), np.ones((3,)))


def test_custom_singularity_value_is_applied() -> None:
    value = point_charge_esp(
        np.zeros((1, 3)),
        np.ones(1),
        np.zeros((1, 3)),
        singularity_value=0.0,
    )

    assert value == pytest.approx((0.0,))


def test_electronic_grid_esp_has_negative_electron_sign_and_bohr_volume() -> None:
    step = 0.5 * BOHR_TO_ANGSTROM
    grid = VolumetricGrid(
        origin=(0.0, 0.0, 0.0),
        axes=((step, 0.0, 0.0), (0.0, step, 0.0), (0.0, 0.0, step)),
        shape=(2, 1, 1),
        values=(4.0, 4.0),
        value_unit="electron/bohr^3",
    )

    value = electronic_esp_from_grid(grid, np.array(((2.0, 0.0, 0.0),)))[0]

    # Two voxels each contain 0.5 electron at x=0 and x=0.5 bohr.
    assert value == pytest.approx(-(0.5 / 2.0 + 0.5 / 1.5))


def test_electronic_grid_esp_far_field_recovers_integrated_electron_charge() -> None:
    step = BOHR_TO_ANGSTROM
    grid = VolumetricGrid(
        origin=(0.0, 0.0, 0.0),
        axes=((step, 0.0, 0.0), (0.0, step, 0.0), (0.0, 0.0, step)),
        shape=(1, 1, 1),
        values=(2.0,),
        value_unit="electron/bohr^3",
    )

    distance = 1_000_000.0
    value = electronic_esp_from_grid(grid, np.array(((distance, 0.0, 0.0),)))[0]

    assert value * distance == pytest.approx(-2.0, rel=1e-10)


def test_total_grid_esp_combines_nuclear_and_electronic_terms() -> None:
    molecule = Molecule(
        atoms=(Atom(1, (0.0, 0.0, 0.0)),),
        charge=0,
        multiplicity=2,
        metadata=CalculationMetadata("fixture"),
    )
    step = BOHR_TO_ANGSTROM
    grid = VolumetricGrid(
        origin=(0.0, 0.0, 0.0),
        axes=((step, 0.0, 0.0), (0.0, step, 0.0), (0.0, 0.0, step)),
        shape=(1, 1, 1),
        values=(1.0,),
        value_unit="electron/bohr^3",
    )

    value = total_esp_from_grid(molecule, grid, np.array(((2.0, 0.0, 0.0),)))[0]

    assert value == pytest.approx(0.0, abs=1e-12)
