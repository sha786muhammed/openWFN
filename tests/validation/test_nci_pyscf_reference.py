"""Independent PySCF reference comparisons for Experimental NCI/RDG fields.

The reference side reconstructs total density, density gradient, and the full
Cartesian density Hessian directly from PySCF AO derivatives and density
matrices. It then derives ordered Hessian eigenvalues, lambda2, RDG, and
sign(lambda2)*rho without importing openWFN's NCI implementation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np
import pytest

from openwfn.api import load

RDG_DENOMINATOR_COEFFICIENT = 2.0 * (3.0 * np.pi**2) ** (1.0 / 3.0)


def _ordinary_points(mol) -> np.ndarray:
    offsets = np.array(
        (
            (0.21, 0.37, 0.29),
            (-0.41, 0.25, 0.33),
            (0.55, -0.31, 0.47),
            (0.19, -0.49, -0.27),
        ),
        dtype=float,
    )
    return mol.atom_coords()[0] + offsets


def _water_dimer_points(mol) -> np.ndarray:
    coordinates = mol.atom_coords()
    donor_h = coordinates[1]
    acceptor_o = coordinates[3]
    midpoint = 0.5 * (donor_h + acceptor_o)
    direction = acceptor_o - donor_h
    direction /= np.linalg.norm(direction)
    return np.array(
        (
            midpoint,
            midpoint + 0.15 * direction,
            midpoint - 0.15 * direction,
            midpoint + np.array((0.12, -0.08, 0.05)),
        ),
        dtype=float,
    )


CASES: tuple[
    tuple[str, str, str, int, int, bool, Callable[[object], np.ndarray]], ...
] = (
    (
        "water",
        "O 0 0 0; H 0 -.757 .587; H 0 .757 .587",
        "sto-3g",
        0,
        0,
        False,
        _ordinary_points,
    ),
    (
        "water_cartesian",
        "O 0 0 0; H 0 -.757 .587; H 0 .757 .587",
        "6-31g*",
        0,
        0,
        True,
        _ordinary_points,
    ),
    (
        "ammonium_cation",
        "N 0 0 0; H .59 .59 .59; H -.59 -.59 .59; H -.59 .59 -.59; H .59 -.59 -.59",
        "6-31g*",
        0,
        1,
        False,
        _ordinary_points,
    ),
    (
        "water_dimer",
        "O 0 0 0; H 0 0 .96; H .93 0 -.24; O 0 0 2.90; H 0 0 3.86; H -.93 0 2.66",
        "6-31g*",
        0,
        0,
        False,
        _water_dimer_points,
    ),
    (
        "oxygen_triplet",
        "O 0 0 -.605; O 0 0 .605",
        "6-31g*",
        2,
        0,
        False,
        _ordinary_points,
    ),
)


def _total_density_matrix(mean_field) -> np.ndarray:
    density_matrix = np.asarray(mean_field.make_rdm1(), dtype=float)
    if density_matrix.ndim == 2:
        return density_matrix
    assert density_matrix.ndim == 3 and density_matrix.shape[0] == 2
    return density_matrix[0] + density_matrix[1]


def _reference_fields(mol, mean_field, points_bohr: np.ndarray):
    from pyscf.dft import numint

    ao = np.asarray(numint.eval_ao(mol, points_bohr, deriv=2), dtype=float)
    values = ao[0]
    gradients = ao[1:4]
    # PySCF deriv=2 order: xx, xy, xz, yy, yz, zz.
    second = {
        (0, 0): ao[4],
        (0, 1): ao[5],
        (1, 0): ao[5],
        (0, 2): ao[6],
        (2, 0): ao[6],
        (1, 1): ao[7],
        (1, 2): ao[8],
        (2, 1): ao[8],
        (2, 2): ao[9],
    }
    dm = _total_density_matrix(mean_field)

    rho = np.einsum("pi,ij,pj->p", values, dm, values, optimize=True)
    gradient = np.empty((len(points_bohr), 3), dtype=float)
    for axis in range(3):
        gradient[:, axis] = 2.0 * np.einsum(
            "pi,ij,pj->p", gradients[axis], dm, values, optimize=True
        )

    hessian = np.empty((len(points_bohr), 3, 3), dtype=float)
    for axis_a in range(3):
        for axis_b in range(3):
            second_term = 2.0 * np.einsum(
                "pi,ij,pj->p",
                second[(axis_a, axis_b)],
                dm,
                values,
                optimize=True,
            )
            gradient_term = 2.0 * np.einsum(
                "pi,ij,pj->p",
                gradients[axis_a],
                dm,
                gradients[axis_b],
                optimize=True,
            )
            hessian[:, axis_a, axis_b] = second_term + gradient_term

    eigenvalues = np.linalg.eigvalsh(0.5 * (hessian + np.swapaxes(hessian, 1, 2)))
    lambda2 = eigenvalues[:, 1]
    gradient_norm = np.linalg.norm(gradient, axis=1)
    rdg = gradient_norm / (RDG_DENOMINATOR_COEFFICIENT * np.power(rho, 4.0 / 3.0))
    signed_density = np.sign(lambda2) * rho
    return rho, gradient, hessian, gradient_norm, eigenvalues, lambda2, rdg, signed_density


def _reference_density_and_gradient(mol, mean_field, points_bohr: np.ndarray):
    from pyscf.dft import numint

    ao = np.asarray(numint.eval_ao(mol, points_bohr, deriv=1), dtype=float)
    values = ao[0]
    gradients = ao[1:4]
    dm = _total_density_matrix(mean_field)
    rho = np.einsum("pi,ij,pj->p", values, dm, values, optimize=True)
    gradient = np.empty((len(points_bohr), 3), dtype=float)
    for axis in range(3):
        gradient[:, axis] = 2.0 * np.einsum(
            "pi,ij,pj->p", gradients[axis], dm, values, optimize=True
        )
    return rho, gradient


def _finite_difference_guard(mol, mean_field, point: np.ndarray) -> None:
    step = 1.0e-4
    _, analytic_gradient = _reference_density_and_gradient(
        mol, mean_field, np.asarray([point], dtype=float)
    )
    _, _, analytic_hessian, *_ = _reference_fields(
        mol, mean_field, np.asarray([point], dtype=float)
    )

    density_gradient_fd = np.empty(3, dtype=float)
    gradient_hessian_fd = np.empty((3, 3), dtype=float)
    for axis in range(3):
        displacement = np.zeros(3, dtype=float)
        displacement[axis] = step
        rho_plus, grad_plus = _reference_density_and_gradient(
            mol, mean_field, np.asarray([point + displacement], dtype=float)
        )
        rho_minus, grad_minus = _reference_density_and_gradient(
            mol, mean_field, np.asarray([point - displacement], dtype=float)
        )
        density_gradient_fd[axis] = (rho_plus[0] - rho_minus[0]) / (2.0 * step)
        gradient_hessian_fd[:, axis] = (grad_plus[0] - grad_minus[0]) / (2.0 * step)

    np.testing.assert_allclose(
        analytic_gradient[0], density_gradient_fd, rtol=2.0e-6, atol=2.0e-8
    )
    np.testing.assert_allclose(
        analytic_hessian[0], gradient_hessian_fd, rtol=2.0e-5, atol=2.0e-7
    )


@pytest.mark.parametrize(
    ("name", "geometry", "basis", "spin", "charge", "cartesian", "point_builder"),
    CASES,
    ids=[case[0] for case in CASES],
)
def test_nci_matches_independent_pyscf_fields(
    name: str,
    geometry: str,
    basis: str,
    spin: int,
    charge: int,
    cartesian: bool,
    point_builder: Callable[[object], np.ndarray],
    tmp_path: Path,
) -> None:
    pytest.importorskip("iodata")
    pytest.importorskip("pyscf")
    from pyscf import gto, lib, scf
    from pyscf.tools import molden

    lib.num_threads(1)
    molecule = gto.M(
        atom=geometry,
        basis=basis,
        spin=spin,
        charge=charge,
        cart=cartesian,
        verbose=0,
    )
    molecule.incore_anyway = True
    mean_field = scf.UHF(molecule) if spin else scf.RHF(molecule)
    mean_field.conv_tol = 1.0e-11
    mean_field.kernel()
    assert mean_field.converged, name

    source = tmp_path / f"{name}.molden"
    molden.from_scf(mean_field, str(source))
    calculation = load(source)
    points = point_builder(molecule)

    (
        rho,
        _gradient,
        _hessian,
        gradient_norm,
        eigenvalues,
        lambda2,
        rdg,
        signed_density,
    ) = _reference_fields(molecule, mean_field, points)
    assert np.all(rho > 1.0e-8), (name, rho)

    result = calculation.analyze("nci", points_bohr=points, chunk_size=2)
    assert result.status == "success", (name, result.error, result.warnings)
    assert result.validation_status == "Experimental"

    np.testing.assert_allclose(
        np.asarray(result.data["rho"], dtype=float), rho, rtol=3.0e-7, atol=3.0e-9
    )
    np.testing.assert_allclose(
        np.asarray(result.data["gradient_norm"], dtype=float),
        gradient_norm,
        rtol=2.0e-6,
        atol=2.0e-8,
    )
    np.testing.assert_allclose(
        np.asarray(result.data["hessian_eigenvalues"], dtype=float),
        eigenvalues,
        rtol=2.0e-5,
        atol=2.0e-7,
    )
    np.testing.assert_allclose(
        np.asarray(result.data["lambda2"], dtype=float),
        lambda2,
        rtol=2.0e-5,
        atol=2.0e-7,
    )
    np.testing.assert_allclose(
        np.asarray(result.data["rdg"], dtype=float), rdg, rtol=4.0e-6, atol=4.0e-8
    )
    np.testing.assert_allclose(
        np.asarray(result.data["signed_density"], dtype=float),
        signed_density,
        rtol=3.0e-7,
        atol=3.0e-9,
    )

    assert result.data["conventions"]["density_channel"] == "total"
    assert result.data["conventions"]["hessian_eigenvalue_order"] == (
        "ascending algebraic"
    )
    assert result.data["conventions"]["signed_density_formula"] == (
        "sign(lambda2)*rho"
    )

    if name in {"water", "water_dimer"}:
        _finite_difference_guard(molecule, mean_field, points[0])
