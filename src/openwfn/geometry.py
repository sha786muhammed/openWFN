# src/openwfn/geometry.py

import math
from collections import Counter
from typing import List, Tuple, Optional, Dict
from .constants import ATOMIC_MASS, Z_TO_SYMBOL, COVALENT_RADII  # type: ignore


def _validate_atom_index(idx_1based: int, n_atoms: int) -> int:
    """Validate 1-based atom index and return 0-based index."""
    if idx_1based < 1 or idx_1based > n_atoms:
        raise ValueError(f"Atom index out of range: {idx_1based} (valid range: 1..{n_atoms})")
    return idx_1based - 1


def distance(i: int, j: int, coordinates: List[Tuple[float, float, float]]) -> float:
    """Calculate Euclidean distance between atom i and j (1-indexed)."""
    n_atoms = len(coordinates)
    i = _validate_atom_index(i, n_atoms)
    j = _validate_atom_index(j, n_atoms)

    xi, yi, zi = coordinates[i]
    xj, yj, zj = coordinates[j]

    dx, dy, dz = xi - xj, yi - yj, zi - zj
    return math.sqrt(dx*dx + dy*dy + dz*dz)


def angle(i: int, j: int, k: int, coordinates: List[Tuple[float, float, float]]) -> float:
    """Calculate bond angle i-j-k in degrees."""
    n_atoms = len(coordinates)
    i = _validate_atom_index(i, n_atoms)
    j = _validate_atom_index(j, n_atoms)
    k = _validate_atom_index(k, n_atoms)

    v1 = [coordinates[i][d] - coordinates[j][d] for d in range(3)]
    v2 = [coordinates[k][d] - coordinates[j][d] for d in range(3)]

    dot = sum(a*b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a*a for a in v1))
    n2 = math.sqrt(sum(a*a for a in v2))
    if n1 == 0.0 or n2 == 0.0:
        raise ValueError("Cannot compute angle for zero-length bond vector.")

    # Clamp cos_t to [-1, 1] to avoid domain errors
    cos_t = max(-1.0, min(1.0, dot/(n1*n2)))
    return math.degrees(math.acos(cos_t))


def dihedral(i: int, j: int, k: int, l: int, coordinates: List[Tuple[float, float, float]]) -> float:
    """Calculate dihedral angle i-j-k-l in degrees."""
    n_atoms = len(coordinates)
    i = _validate_atom_index(i, n_atoms)
    j = _validate_atom_index(j, n_atoms)
    k = _validate_atom_index(k, n_atoms)
    l = _validate_atom_index(l, n_atoms)

    def vec(a, b):
        return [b[d] - a[d] for d in range(3)]

    def cross(u, v):
        return [
            u[1]*v[2] - u[2]*v[1],
            u[2]*v[0] - u[0]*v[2],
            u[0]*v[1] - u[1]*v[0]
        ]

    def dot(u, v):
        return sum(u[d]*v[d] for d in range(3))

    b1 = vec(coordinates[j], coordinates[i])
    b2 = vec(coordinates[j], coordinates[k])
    b3 = vec(coordinates[l], coordinates[k])

    n1 = cross(b1, b2)
    n2 = cross(b2, b3)
    m1 = cross(n1, b2)
    b2_norm = math.sqrt(dot(b2, b2))
    if b2_norm == 0.0:
        raise ValueError("Cannot compute dihedral for zero-length central bond vector.")

    x = dot(n1, n2)
    y = dot(m1, n2) / b2_norm

    return math.degrees(math.atan2(y, x))


def molecular_formula(atomic_numbers: List[int]) -> str:
    """Generate Hill system molecular formula."""
    counts: Dict[int, int] = {}
    for z in atomic_numbers:
        counts[z] = counts.get(z, 0) + 1

    # Hill system ordering: C, H, then alphabetical
    elements: List[int] = []
    if 6 in counts:
        elements.append(6)
    if 1 in counts:
        elements.append(1)

    for Z in sorted(counts.keys()):
        if Z not in elements:
            elements.append(Z)

    formula = ""
    for Z in elements:
        sym = Z_TO_SYMBOL.get(Z, f"Z{Z}")
        n = counts[Z]
        formula += f"{sym}{n if n>1 else ''}"

    return formula


def center_of_mass(atomic_numbers: List[int], coordinates: List[Tuple[float, float, float]]) -> Tuple[float, float, float]:
    """Calculate center of mass."""
    total_mass = 0.0
    cx = cy = cz = 0.0

    for Z, (x, y, z) in zip(atomic_numbers, coordinates):
        if Z not in ATOMIC_MASS:
            exclude_sys = Z_TO_SYMBOL.get(Z, f"Z={Z}")
            raise ValueError(f"Unknown atomic mass for element: {exclude_sys}")
            
        m = ATOMIC_MASS[Z]
        total_mass += m
        cx += m * x
        cy += m * y
        cz += m * z

    if total_mass == 0.0:
        return 0.0, 0.0, 0.0

    return cx/total_mass, cy/total_mass, cz/total_mass


def detect_bonds(atomic_numbers: List[int], coordinates: List[Tuple[float, float, float]], scale: float = 1.2) -> List[Tuple[int, int, float]]:
    """
    Detect covalent bonds based on interatomic distances.
    Returns list of (atom_i, atom_j, distance).
    """
    bonds: List[Tuple[int, int, float]] = []
    n = len(atomic_numbers)

    for i in range(n):
        Zi = atomic_numbers[i]  # type: ignore
        sym_i = Z_TO_SYMBOL.get(Zi)
        ri = COVALENT_RADII.get(sym_i)

        if ri is None:
            continue

        for j in range(i+1, n):
            Zj = atomic_numbers[j]  # type: ignore
            sym_j = Z_TO_SYMBOL.get(Zj)
            rj = COVALENT_RADII.get(sym_j)

            if rj is None:
                continue

            d = distance(i+1, j+1, coordinates)
            cutoff = scale * (ri + rj)

            if d <= cutoff:
                bonds.append((i+1, j+1, d))

    return bonds
