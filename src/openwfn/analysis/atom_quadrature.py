"""Deterministic bounded atom-centered quadrature for molecular integration."""

from collections.abc import Iterator
from dataclasses import dataclass
from math import isfinite, pi

import numpy as np

from openwfn.constants import BOHR_TO_ANGSTROM
from openwfn.model import Molecule

from .limits import MAX_ATOM_QUADRATURE_POINTS

_COINCIDENT_CENTER_TOLERANCE_BOHR = 1.0e-12
_LOG_FLOOR = np.finfo(float).tiny


@dataclass(frozen=True, slots=True)
class AtomQuadratureSettings:
    """Numerical controls for deterministic atom-centered molecular quadrature."""

    radial_points: int = 96
    theta_points: int = 18
    phi_points: int = 36
    radial_extent_bohr: float = 20.0
    chunk_size: int = 65_536

    def __post_init__(self) -> None:
        if self.radial_points < 2:
            raise ValueError("radial_points must be at least 2")
        if self.theta_points < 2:
            raise ValueError("theta_points must be at least 2")
        if self.phi_points < 4:
            raise ValueError("phi_points must be at least 4")
        if not isfinite(self.radial_extent_bohr) or self.radial_extent_bohr <= 0.0:
            raise ValueError("radial_extent_bohr must be finite and positive")
        if self.chunk_size < 1:
            raise ValueError("chunk_size must be positive")


@dataclass(frozen=True, slots=True)
class AtomQuadratureChunk:
    """One bounded block of an atom-centered molecular quadrature."""

    points_bohr: np.ndarray
    integration_weights: np.ndarray
    owner_atom_indices: np.ndarray
    molecular_partition_weights: np.ndarray


def _becke_polynomial(value: np.ndarray) -> np.ndarray:
    """Apply Becke's smooth odd switching polynomial three times."""

    transformed = np.clip(value, -1.0, 1.0)
    for _ in range(3):
        transformed = 1.5 * transformed - 0.5 * transformed**3
    return transformed


def _becke_partition_weights(points_bohr: np.ndarray, centers_bohr: np.ndarray) -> np.ndarray:
    """Return smooth Becke-style molecular partition weights for each point/center."""

    points = np.asarray(points_bohr, dtype=float)
    centers = np.asarray(centers_bohr, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points_bohr must have shape (n_points, 3)")
    if centers.ndim != 2 or centers.shape[1] != 3 or centers.shape[0] < 1:
        raise ValueError("centers_bohr must have shape (n_atoms, 3)")
    if not np.all(np.isfinite(points)) or not np.all(np.isfinite(centers)):
        raise ValueError("quadrature points and centers must be finite")

    n_points = points.shape[0]
    n_centers = centers.shape[0]
    if n_centers == 1:
        return np.ones((n_points, 1), dtype=float)

    pair_distances = np.linalg.norm(centers[:, None, :] - centers[None, :, :], axis=2)
    upper = pair_distances[np.triu_indices(n_centers, k=1)]
    if np.any(upper <= _COINCIDENT_CENTER_TOLERANCE_BOHR):
        raise ValueError("coincident atomic centers are not supported by molecular partitioning")

    point_distances = np.linalg.norm(points[:, None, :] - centers[None, :, :], axis=2)
    log_weights = np.zeros((n_points, n_centers), dtype=float)

    for atom_a in range(n_centers - 1):
        for atom_b in range(atom_a + 1, n_centers):
            separation = pair_distances[atom_a, atom_b]
            mu = (point_distances[:, atom_a] - point_distances[:, atom_b]) / separation
            switched = _becke_polynomial(mu)
            factor_a = 0.5 * (1.0 - switched)
            factor_b = 1.0 - factor_a
            log_weights[:, atom_a] += np.log(np.clip(factor_a, _LOG_FLOOR, 1.0))
            log_weights[:, atom_b] += np.log(np.clip(factor_b, _LOG_FLOOR, 1.0))

    log_weights -= np.max(log_weights, axis=1, keepdims=True)
    weights = np.exp(log_weights)
    normalizer = np.sum(weights, axis=1, keepdims=True)
    if np.any(~np.isfinite(normalizer)) or np.any(normalizer <= 0.0):
        raise ValueError("molecular partition normalization failed")
    weights /= normalizer
    return weights


def _centers_bohr(molecule: Molecule) -> np.ndarray:
    return np.asarray([atom.coordinates for atom in molecule.atoms], dtype=float) / BOHR_TO_ANGSTROM


def iter_atom_centered_chunks(
    molecule: Molecule,
    settings: AtomQuadratureSettings,
) -> Iterator[AtomQuadratureChunk]:
    """Yield deterministic atom-centered quadrature chunks with molecular partitioning.

    ``integration_weights`` already include the owner atom's smooth molecular
    partition weight. ``molecular_partition_weights`` exposes that factor
    separately for diagnostics.
    """

    atom_count = len(molecule.atoms)
    points_per_atom = settings.radial_points * settings.theta_points * settings.phi_points
    total_points = atom_count * points_per_atom
    if total_points > MAX_ATOM_QUADRATURE_POINTS:
        raise ValueError(
            f"quadrature point count {total_points} exceeds safety limit "
            f"{MAX_ATOM_QUADRATURE_POINTS}"
        )

    centers = _centers_bohr(molecule)
    if atom_count > 1:
        pair_distances = np.linalg.norm(centers[:, None, :] - centers[None, :, :], axis=2)
        upper = pair_distances[np.triu_indices(atom_count, k=1)]
        if np.any(upper <= _COINCIDENT_CENTER_TOLERANCE_BOHR):
            raise ValueError("coincident atomic centers are not supported by molecular partitioning")

    radial_x, radial_w = np.polynomial.legendre.leggauss(settings.radial_points)
    radius = 0.5 * settings.radial_extent_bohr * (radial_x + 1.0)
    radial_weight = 0.5 * settings.radial_extent_bohr * radial_w

    cos_theta, theta_weight = np.polynomial.legendre.leggauss(settings.theta_points)
    phi = 2.0 * pi * np.arange(settings.phi_points, dtype=float) / settings.phi_points
    phi_weight = 2.0 * pi / settings.phi_points
    angular_stride = settings.theta_points * settings.phi_points

    for owner_atom_index in range(atom_count):
        owner_center = centers[owner_atom_index]
        for start in range(0, points_per_atom, settings.chunk_size):
            stop = min(start + settings.chunk_size, points_per_atom)
            flat_index = np.arange(start, stop, dtype=np.int64)
            radial_index = flat_index // angular_stride
            angular_index = flat_index % angular_stride
            theta_index = angular_index // settings.phi_points
            phi_index = angular_index % settings.phi_points

            r = radius[radial_index]
            z = cos_theta[theta_index]
            transverse = np.sqrt(np.maximum(0.0, 1.0 - z * z))
            angle = phi[phi_index]
            local_points = np.column_stack(
                (
                    r * transverse * np.cos(angle),
                    r * transverse * np.sin(angle),
                    r * z,
                )
            )
            points = local_points + owner_center

            base_weights = (
                radial_weight[radial_index]
                * r
                * r
                * theta_weight[theta_index]
                * phi_weight
            )
            partition = _becke_partition_weights(points, centers)
            owner_partition = partition[:, owner_atom_index]
            integration_weights = base_weights * owner_partition

            yield AtomQuadratureChunk(
                points_bohr=points,
                integration_weights=integration_weights,
                owner_atom_indices=np.full(points.shape[0], owner_atom_index, dtype=np.int64),
                molecular_partition_weights=owner_partition,
            )
