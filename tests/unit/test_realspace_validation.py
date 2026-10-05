import json
from pathlib import Path

import numpy as np
import pytest

from openwfn.analysis.basis import evaluate_ao, evaluate_ao_fields
from openwfn.analysis.realspace import evaluate_density_fields
from openwfn.constants import BOHR_TO_ANGSTROM
from openwfn.model import (
    Atom,
    BasisSet,
    BasisShell,
    CalculationData,
    CalculationMetadata,
    DensityMatrix,
    Molecule,
)

REFERENCE = Path(__file__).resolve().parents[1] / "reference_data" / "realspace_sympy_dxy.json"


def _molecule_at_bohr(center_bohr: np.ndarray) -> Molecule:
    center_angstrom = tuple((np.asarray(center_bohr, dtype=float) * BOHR_TO_ANGSTROM).tolist())
    return Molecule(
        (Atom(1, center_angstrom),),
        0,
        1,
        CalculationMetadata("realspace-validation-fixture"),
    )


def _finite_difference_ao(
    basis: BasisSet,
    molecule: Molecule,
    point: np.ndarray,
    *,
    step: float = 3.0e-4,
) -> tuple[np.ndarray, np.ndarray]:
    point = np.asarray(point, dtype=float)

    def values(offset: np.ndarray) -> np.ndarray:
        return evaluate_ao(basis, molecule, (point + offset).reshape(1, 3))[0]

    origin = values(np.zeros(3))
    gradient = np.zeros((origin.size, 3), dtype=float)
    hessian = np.zeros((origin.size, 3, 3), dtype=float)

    for axis in range(3):
        offset = np.zeros(3)
        offset[axis] = step
        plus = values(offset)
        minus = values(-offset)
        gradient[:, axis] = (plus - minus) / (2.0 * step)
        hessian[:, axis, axis] = (plus - 2.0 * origin + minus) / step**2

    for left in range(3):
        for right in range(left):
            offset_left = np.zeros(3)
            offset_right = np.zeros(3)
            offset_left[left] = step
            offset_right[right] = step
            mixed = (
                values(offset_left + offset_right)
                - values(offset_left - offset_right)
                - values(-offset_left + offset_right)
                + values(-offset_left - offset_right)
            ) / (4.0 * step**2)
            hessian[:, left, right] = mixed
            hessian[:, right, left] = mixed

    return gradient, hessian


@pytest.mark.parametrize("angular_momentum", (0, 1, 2, 3, 4, 5))
def test_analytic_ao_derivatives_match_central_finite_differences_through_h(
    angular_momentum: int,
) -> None:
    basis = BasisSet(
        (
            BasisShell(
                0,
                angular_momentum,
                (0.8,),
                (1.0,),
                pure=angular_momentum >= 2,
            ),
        )
    )
    molecule = _molecule_at_bohr(np.zeros(3))
    point = np.array((0.31, -0.27, 0.42), dtype=float)

    analytic = evaluate_ao_fields(basis, molecule, point.reshape(1, 3), derivatives=2)
    fd_gradient, fd_hessian = _finite_difference_ao(basis, molecule, point)

    np.testing.assert_allclose(
        analytic.gradients[0],
        fd_gradient,
        rtol=5.0e-6,
        atol=5.0e-7,
    )
    np.testing.assert_allclose(
        analytic.hessians[0],
        fd_hessian,
        rtol=8.0e-5,
        atol=8.0e-6,
    )


def test_ao_fields_are_invariant_when_molecule_and_points_translate_together() -> None:
    center = np.array((0.24, -0.18, 0.37), dtype=float)
    shift = np.array((1.1, -0.65, 0.48), dtype=float)
    points = np.array(
        (
            (0.61, -0.44, 0.82),
            (-0.13, 0.21, 0.57),
        ),
        dtype=float,
    )
    basis = BasisSet((BasisShell(0, 4, (0.75,), (1.0,), pure=True),))

    baseline = evaluate_ao_fields(basis, _molecule_at_bohr(center), points)
    translated = evaluate_ao_fields(
        basis,
        _molecule_at_bohr(center + shift),
        points + shift,
    )

    np.testing.assert_allclose(translated.values, baseline.values, rtol=0.0, atol=2.0e-12)
    np.testing.assert_allclose(translated.gradients, baseline.gradients, rtol=0.0, atol=3.0e-12)
    np.testing.assert_allclose(translated.hessians, baseline.hessians, rtol=0.0, atol=5.0e-12)


def test_density_hessian_eigenvalues_are_finite_and_stable_under_symmetrization() -> None:
    molecule = _molecule_at_bohr(np.zeros(3))
    basis = BasisSet(
        (
            BasisShell(0, 0, (0.7,), (1.0,)),
            BasisShell(0, 0, (1.3,), (1.0,)),
        )
    )
    density = DensityMatrix(((1.2, 0.15), (0.15, 0.8)), "total")
    data = CalculationData(molecule=molecule, basis=basis, total_density=density)
    points = np.array(
        (
            (0.31, -0.27, 0.42),
            (-0.36, 0.19, 0.28),
            (0.22, 0.34, -0.41),
        ),
        dtype=float,
    )

    fields = evaluate_density_fields(data, points)

    for hessian in fields.hessian:
        assert np.all(np.isfinite(hessian))
        symmetrized = 0.5 * (hessian + hessian.T)
        np.testing.assert_allclose(hessian, symmetrized, rtol=0.0, atol=2.0e-13)
        eigenvalues = np.linalg.eigvalsh(hessian)
        symmetrized_eigenvalues = np.linalg.eigvalsh(symmetrized)
        assert np.all(np.isfinite(eigenvalues))
        np.testing.assert_allclose(
            eigenvalues,
            symmetrized_eigenvalues,
            rtol=2.0e-13,
            atol=2.0e-13,
        )


def test_cartesian_dxy_matches_independent_sympy_symbolic_reference() -> None:
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    provenance = reference["provenance"]
    assert provenance["generator"] == "SymPy 1.14.0"
    assert provenance["method"].startswith("Independent symbolic differentiation")

    basis = BasisSet((BasisShell(0, 2, (float(provenance["alpha"]),), (1.0,), pure=False),))
    molecule = _molecule_at_bohr(np.zeros(3))
    point = np.asarray(provenance["point_bohr"], dtype=float).reshape(1, 3)

    fields = evaluate_ao_fields(basis, molecule, point)
    dxy_index = 3

    assert fields.values[0, dxy_index] == pytest.approx(reference["value"], abs=2.0e-14)
    np.testing.assert_allclose(
        fields.gradients[0, dxy_index],
        np.asarray(reference["gradient"]),
        rtol=0.0,
        atol=3.0e-14,
    )
    np.testing.assert_allclose(
        fields.hessians[0, dxy_index],
        np.asarray(reference["hessian"]),
        rtol=0.0,
        atol=5.0e-14,
    )
