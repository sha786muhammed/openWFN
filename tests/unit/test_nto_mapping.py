from __future__ import annotations

import numpy as np
import pytest

from openwfn.analysis.basis import overlap_matrix
from openwfn.errors import DataUnavailableError
from openwfn.excited_states import AmplitudeBlock
from openwfn.model import (
    Atom,
    BasisSet,
    BasisShell,
    CalculationData,
    CalculationMetadata,
    MolecularOrbitals,
    Molecule,
)


def _orthonormal_restricted_calculation(*, coefficient_scale: float = 1.0) -> tuple[CalculationData, np.ndarray]:
    molecule = Molecule(
        atoms=tuple(Atom(1, (3.0 * index, 0.0, 0.0)) for index in range(4)),
        charge=0,
        multiplicity=1,
        metadata=CalculationMetadata("analytic"),
    )
    basis = BasisSet(tuple(BasisShell(index, 0, (1.0,), (1.0,)) for index in range(4)))
    overlap = overlap_matrix(basis, molecule)
    eigenvalues, eigenvectors = np.linalg.eigh(overlap)
    coefficients = eigenvectors @ np.diag(eigenvalues ** -0.5) @ eigenvectors.T
    coefficients *= coefficient_scale
    orbitals = MolecularOrbitals(
        energies=(-0.9, -0.5, 0.2, 0.6),
        coefficients=tuple(tuple(float(value) for value in row) for row in coefficients),
        occupations=(2.0, 2.0, 0.0, 0.0),
        spin="restricted",
    )
    return CalculationData(molecule=molecule, basis=basis, alpha_orbitals=orbitals), coefficients


def _block(values=(0.8, 0.2, 0.1, 0.4), *, spin_block=None, dimensions=(2, 2)) -> AmplitudeBlock:
    return AmplitudeBlock(
        convention="cis-transition-amplitude-matrix",
        values=tuple(float(value) for value in values),
        dimensions=dimensions,
        spin_block=spin_block,
    )


def test_restricted_nto_mapping_rotates_source_occ_and_virtual_mos_into_ao_basis() -> None:
    from openwfn.analysis.nto import compute_nto_svd, map_nto_to_ao, transition_matrix_from_block

    data, source_coefficients = _orthonormal_restricted_calculation()
    block = _block()
    svd = compute_nto_svd(transition_matrix_from_block(block))

    mapped = map_nto_to_ao(data, block)

    np.testing.assert_allclose(
        mapped.hole_coefficients,
        source_coefficients[:, :2] @ svd.hole_vectors,
        atol=1e-12,
    )
    np.testing.assert_allclose(
        mapped.electron_coefficients,
        source_coefficients[:, 2:] @ svd.electron_vectors,
        atol=1e-12,
    )
    np.testing.assert_allclose(mapped.hole_norms, np.ones(2), atol=1e-12)
    np.testing.assert_allclose(mapped.electron_norms, np.ones(2), atol=1e-12)
    np.testing.assert_allclose(mapped.hole_norm_residuals, np.zeros(2), atol=1e-12)
    np.testing.assert_allclose(mapped.electron_norm_residuals, np.zeros(2), atol=1e-12)
    assert mapped.occupied_mo_indices == (1, 2)
    assert mapped.virtual_mo_indices == (3, 4)
    assert mapped.spin_block == "restricted"


def test_nto_mapping_reports_bad_source_norm_without_silent_renormalization() -> None:
    from openwfn.analysis.nto import map_nto_to_ao

    data, source_coefficients = _orthonormal_restricted_calculation(coefficient_scale=2.0)
    mapped = map_nto_to_ao(data, _block())

    assert np.all(mapped.hole_norms > 3.9)
    assert np.all(mapped.electron_norms > 3.9)
    assert np.all(mapped.hole_norm_residuals > 2.9)
    assert np.all(mapped.electron_norm_residuals > 2.9)
    assert np.max(np.abs(mapped.hole_coefficients)) > np.max(np.abs(source_coefficients[:, :2])) * 0.4


def test_nto_mapping_rejects_transition_dimensions_that_do_not_match_occ_virtual_sets() -> None:
    from openwfn.analysis.nto import map_nto_to_ao

    data, _ = _orthonormal_restricted_calculation()
    block = _block(values=(0.8, 0.2, 0.1, 0.4), dimensions=(1, 4))

    with pytest.raises(DataUnavailableError, match="dimensions.*occupied.*virtual"):
        map_nto_to_ao(data, block)


def test_nto_mapping_rejects_missing_basis() -> None:
    from openwfn.analysis.nto import map_nto_to_ao

    data, _ = _orthonormal_restricted_calculation()
    without_basis = CalculationData(
        molecule=data.molecule,
        alpha_orbitals=data.alpha_orbitals,
    )
    with pytest.raises(DataUnavailableError, match="basis"):
        map_nto_to_ao(without_basis, _block())


def test_nto_mapping_rejects_unrestricted_block_without_explicit_spin() -> None:
    from openwfn.analysis.nto import map_nto_to_ao

    data, coefficients = _orthonormal_restricted_calculation()
    alpha = MolecularOrbitals(
        (-0.8, 0.3),
        tuple(tuple(float(value) for value in row[:2]) for row in coefficients),
        (1.0, 0.0),
        "alpha",
    )
    beta = MolecularOrbitals(
        (-0.7, 0.4),
        tuple(tuple(float(value) for value in row[:2]) for row in coefficients),
        (1.0, 0.0),
        "beta",
    )
    unrestricted = CalculationData(
        molecule=data.molecule,
        basis=data.basis,
        alpha_orbitals=alpha,
        beta_orbitals=beta,
    )
    block = AmplitudeBlock(
        convention="cis-transition-amplitude-matrix",
        values=(1.0,),
        dimensions=(1, 1),
    )

    with pytest.raises(DataUnavailableError, match="spin"):
        map_nto_to_ao(unrestricted, block)


def test_nto_mapping_uses_requested_unrestricted_spin_channel() -> None:
    from openwfn.analysis.nto import map_nto_to_ao

    data, coefficients = _orthonormal_restricted_calculation()
    alpha_coeff = coefficients[:, (0, 2)]
    beta_coeff = coefficients[:, (1, 3)]
    alpha = MolecularOrbitals(
        (-0.8, 0.3),
        tuple(tuple(float(value) for value in row) for row in alpha_coeff),
        (1.0, 0.0),
        "alpha",
    )
    beta = MolecularOrbitals(
        (-0.7, 0.4),
        tuple(tuple(float(value) for value in row) for row in beta_coeff),
        (1.0, 0.0),
        "beta",
    )
    unrestricted = CalculationData(
        molecule=data.molecule,
        basis=data.basis,
        alpha_orbitals=alpha,
        beta_orbitals=beta,
    )

    mapped_alpha = map_nto_to_ao(
        unrestricted,
        AmplitudeBlock(
            convention="cis-transition-amplitude-matrix",
            values=(1.0,),
            dimensions=(1, 1),
            spin_block="alpha",
        ),
    )
    mapped_beta = map_nto_to_ao(
        unrestricted,
        AmplitudeBlock(
            convention="cis-transition-amplitude-matrix",
            values=(1.0,),
            dimensions=(1, 1),
            spin_block="beta",
        ),
    )

    np.testing.assert_allclose(mapped_alpha.hole_coefficients[:, 0], alpha_coeff[:, 0], atol=1e-12)
    np.testing.assert_allclose(mapped_beta.hole_coefficients[:, 0], beta_coeff[:, 0], atol=1e-12)
    assert mapped_alpha.spin_block == "alpha"
    assert mapped_beta.spin_block == "beta"
