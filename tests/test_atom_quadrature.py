import numpy as np
import pytest

from openwfn.analysis.atom_quadrature import (
    AtomQuadratureSettings,
    _becke_partition_weights,
    iter_atom_centered_chunks,
)
from openwfn.constants import BOHR_TO_ANGSTROM
from openwfn.model import Atom, CalculationMetadata, Molecule


def _molecule(coordinates_angstrom: list[tuple[float, float, float]]) -> Molecule:
    return Molecule(
        atoms=tuple(Atom(1, coordinates) for coordinates in coordinates_angstrom),
        charge=0,
        multiplicity=1,
        metadata=CalculationMetadata(source_program="quadrature-test"),
    )


def _collect(molecule: Molecule, settings: AtomQuadratureSettings):
    chunks = tuple(iter_atom_centered_chunks(molecule, settings))
    points = np.concatenate([chunk.points_bohr for chunk in chunks], axis=0)
    weights = np.concatenate([chunk.integration_weights for chunk in chunks], axis=0)
    owners = np.concatenate([chunk.owner_atom_indices for chunk in chunks], axis=0)
    partitions = np.concatenate([chunk.molecular_partition_weights for chunk in chunks], axis=0)
    return chunks, points, weights, owners, partitions


def test_one_atom_constant_integrates_sphere_volume() -> None:
    radius = 5.0
    settings = AtomQuadratureSettings(
        radial_points=24,
        theta_points=8,
        phi_points=16,
        radial_extent_bohr=radius,
        chunk_size=257,
    )
    molecule = _molecule([(0.0, 0.0, 0.0)])

    _, _, weights, _, partitions = _collect(molecule, settings)

    expected = 4.0 * np.pi * radius**3 / 3.0
    assert np.isclose(float(np.sum(weights)), expected, rtol=0.0, atol=1.0e-11)
    np.testing.assert_allclose(partitions, 1.0, rtol=0.0, atol=0.0)


def test_one_atom_spherical_gaussian_matches_analytic_integral() -> None:
    alpha = 0.7
    settings = AtomQuadratureSettings(
        radial_points=64,
        theta_points=8,
        phi_points=16,
        radial_extent_bohr=9.0,
        chunk_size=1000,
    )
    molecule = _molecule([(0.0, 0.0, 0.0)])

    _, points, weights, _, _ = _collect(molecule, settings)
    values = np.exp(-alpha * np.einsum("pi,pi->p", points, points))
    integrated = float(np.dot(values, weights))
    expected = (np.pi / alpha) ** 1.5

    assert np.isclose(integrated, expected, rtol=0.0, atol=1.0e-10)


def test_becke_partition_is_bounded_and_sums_to_one() -> None:
    centers = np.array([[-1.2, 0.0, 0.0], [1.2, 0.0, 0.0]])
    points = np.array(
        [
            [-2.0, 0.3, 0.0],
            [0.0, 0.0, 0.0],
            [0.4, -0.7, 0.2],
            [2.0, 0.0, -0.5],
        ]
    )

    partition = _becke_partition_weights(points, centers)

    assert partition.shape == (4, 2)
    assert np.all(np.isfinite(partition))
    assert np.all(partition >= 0.0)
    assert np.all(partition <= 1.0)
    np.testing.assert_allclose(np.sum(partition, axis=1), 1.0, rtol=0.0, atol=1.0e-14)
    np.testing.assert_allclose(partition[1], [0.5, 0.5], rtol=0.0, atol=1.0e-14)


def test_quadrature_is_translation_invariant_and_deterministic() -> None:
    settings = AtomQuadratureSettings(
        radial_points=16,
        theta_points=6,
        phi_points=12,
        radial_extent_bohr=6.0,
        chunk_size=311,
    )
    original = _molecule([(-0.4, 0.0, 0.0), (0.4, 0.0, 0.0)])
    shift_angstrom = np.array([1.7, -0.6, 0.25])
    shifted = _molecule(
        [tuple(np.asarray(atom.coordinates) + shift_angstrom) for atom in original.atoms]
    )

    first = _collect(original, settings)
    repeated = _collect(original, settings)
    translated = _collect(shifted, settings)

    for left, right in zip(first[1:], repeated[1:]):
        np.testing.assert_array_equal(left, right)
    np.testing.assert_allclose(
        translated[1] - shift_angstrom / BOHR_TO_ANGSTROM,
        first[1],
        rtol=0.0,
        atol=2.0e-14,
    )
    np.testing.assert_allclose(translated[2], first[2], rtol=0.0, atol=2.0e-14)
    np.testing.assert_array_equal(translated[3], first[3])
    np.testing.assert_allclose(translated[4], first[4], rtol=0.0, atol=2.0e-14)


def test_chunks_are_bounded_and_weights_are_finite_nonnegative() -> None:
    settings = AtomQuadratureSettings(
        radial_points=18,
        theta_points=8,
        phi_points=10,
        radial_extent_bohr=7.0,
        chunk_size=127,
    )
    molecule = _molecule([(-0.5, 0.0, 0.0), (0.5, 0.0, 0.0), (0.0, 0.7, 0.0)])

    chunks = tuple(iter_atom_centered_chunks(molecule, settings))

    assert chunks
    assert all(0 < chunk.points_bohr.shape[0] <= settings.chunk_size for chunk in chunks)
    for chunk in chunks:
        assert chunk.points_bohr.shape[1] == 3
        assert np.all(np.isfinite(chunk.points_bohr))
        assert np.all(np.isfinite(chunk.integration_weights))
        assert np.all(chunk.integration_weights >= 0.0)
        assert np.all(np.isfinite(chunk.molecular_partition_weights))
        assert np.all(chunk.molecular_partition_weights >= 0.0)
        assert np.all(chunk.molecular_partition_weights <= 1.0)


def test_unreasonable_grid_is_rejected_before_allocation() -> None:
    molecule = _molecule([(0.0, 0.0, 0.0), (0.8, 0.0, 0.0)])
    settings = AtomQuadratureSettings(
        radial_points=10_000,
        theta_points=1_000,
        phi_points=1_000,
        radial_extent_bohr=20.0,
        chunk_size=65_536,
    )

    with pytest.raises(ValueError, match="quadrature point count .* exceeds"):
        next(iter_atom_centered_chunks(molecule, settings))


def test_invalid_quadrature_settings_fail_explicitly() -> None:
    with pytest.raises(ValueError, match="radial_points"):
        AtomQuadratureSettings(radial_points=1)
    with pytest.raises(ValueError, match="theta_points"):
        AtomQuadratureSettings(theta_points=1)
    with pytest.raises(ValueError, match="phi_points"):
        AtomQuadratureSettings(phi_points=3)
    with pytest.raises(ValueError, match="radial_extent_bohr"):
        AtomQuadratureSettings(radial_extent_bohr=0.0)
    with pytest.raises(ValueError, match="chunk_size"):
        AtomQuadratureSettings(chunk_size=0)
