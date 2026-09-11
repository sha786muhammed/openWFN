"""Advanced molecular geometry calculations."""

import numpy as np

from ..constants import ATOMIC_MASS
from ..model import Molecule


def _coordinates_and_masses(molecule: Molecule) -> tuple[np.ndarray, np.ndarray]:
    coordinates = np.asarray([atom.coordinates for atom in molecule.atoms], dtype=float)
    masses = np.asarray([ATOMIC_MASS[atom.atomic_number] for atom in molecule.atoms], dtype=float)
    return coordinates, masses


def _centered_coordinates(molecule: Molecule) -> tuple[np.ndarray, np.ndarray]:
    coordinates, masses = _coordinates_and_masses(molecule)
    center = np.average(coordinates, axis=0, weights=masses)
    return coordinates - center, masses


def inertia_tensor(molecule: Molecule) -> np.ndarray:
    """Return the mass-weighted inertia tensor in amu·Å² about the center of mass."""

    centered, masses = _centered_coordinates(molecule)
    tensor = np.zeros((3, 3), dtype=float)
    identity = np.eye(3)
    for coordinate, mass in zip(centered, masses):
        tensor += mass * (
            np.dot(coordinate, coordinate) * identity - np.outer(coordinate, coordinate)
        )
    return tensor


def principal_axes(molecule: Molecule) -> tuple[np.ndarray, np.ndarray]:
    """Return ascending principal moments and orthonormal principal axes."""

    moments, axes = np.linalg.eigh(inertia_tensor(molecule))
    return moments, axes


def radius_of_gyration(molecule: Molecule) -> float:
    """Return the mass-weighted radius of gyration in ångström."""

    centered, masses = _centered_coordinates(molecule)
    return float(np.sqrt(np.sum(masses * np.sum(centered * centered, axis=1)) / np.sum(masses)))


def kabsch_rmsd(reference: Molecule, mobile: Molecule) -> float:
    """Return optimal rigid-body RMSD in ångström without permuting atoms."""

    reference_elements = tuple(atom.atomic_number for atom in reference.atoms)
    mobile_elements = tuple(atom.atomic_number for atom in mobile.atoms)
    if reference_elements != mobile_elements:
        raise ValueError("molecules must have identical atom counts and element ordering")
    reference_coordinates = np.asarray([atom.coordinates for atom in reference.atoms], dtype=float)
    mobile_coordinates = np.asarray([atom.coordinates for atom in mobile.atoms], dtype=float)
    reference_centered = reference_coordinates - reference_coordinates.mean(axis=0)
    mobile_centered = mobile_coordinates - mobile_coordinates.mean(axis=0)
    covariance = mobile_centered.T @ reference_centered
    left, _, right_transposed = np.linalg.svd(covariance)
    correction = np.eye(3)
    correction[-1, -1] = np.sign(np.linalg.det(right_transposed.T @ left.T))
    rotation = right_transposed.T @ correction @ left.T
    aligned = mobile_centered @ rotation.T
    return float(np.sqrt(np.mean(np.sum((aligned - reference_centered) ** 2, axis=1))))
