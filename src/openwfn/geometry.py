# src/openwfn/geometry.py

import math
from collections import Counter
from openwfn.constants import ATOMIC_MASS, Z_TO_SYMBOL, COVALENT_RADII


def distance(i, j, coordinates):
    i -= 1
    j -= 1

    xi, yi, zi = coordinates[i]
    xj, yj, zj = coordinates[j]

    dx, dy, dz = xi - xj, yi - yj, zi - zj
    return math.sqrt(dx*dx + dy*dy + dz*dz)


def angle(i, j, k, coordinates):
    i, j, k = i-1, j-1, k-1

    v1 = [coordinates[i][d] - coordinates[j][d] for d in range(3)]
    v2 = [coordinates[k][d] - coordinates[j][d] for d in range(3)]

    dot = sum(a*b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a*a for a in v1))
    n2 = math.sqrt(sum(a*a for a in v2))

    cos_t = max(-1.0, min(1.0, dot/(n1*n2)))
    return math.degrees(math.acos(cos_t))


def dihedral(i, j, k, l, coordinates):
    i, j, k, l = i-1, j-1, k-1, l-1

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

    x = dot(n1, n2)
    y = dot(m1, n2) / math.sqrt(dot(b2, b2))

    return math.degrees(math.atan2(y, x))


def molecular_formula(atomic_numbers):
    counts = Counter(atomic_numbers)

    # Hill system ordering: C, H, then alphabetical
    elements = []
    if 6 in counts:
        elements.append(6)
    if 1 in counts:
        elements.append(1)

    for Z in sorted(counts):
        if Z not in elements:
            elements.append(Z)

    formula = ""
    for Z in elements:
        sym = Z_TO_SYMBOL.get(Z, f"Z{Z}")
        n = counts[Z]
        formula += f"{sym}{n if n>1 else ''}"

    return formula


def center_of_mass(atomic_numbers, coordinates):
    total_mass = 0.0
    cx = cy = cz = 0.0

    for Z, (x, y, z) in zip(atomic_numbers, coordinates):
        m = ATOMIC_MASS.get(Z, 12.0)
        total_mass += m
        cx += m * x
        cy += m * y
        cz += m * z

    return cx/total_mass, cy/total_mass, cz/total_mass


def detect_bonds(atomic_numbers, coordinates, scale=1.2):
    bonds = []
    n = len(atomic_numbers)

    for i in range(n):
        Zi = atomic_numbers[i]
        sym_i = Z_TO_SYMBOL.get(Zi)
        ri = COVALENT_RADII.get(sym_i)

        if ri is None:
            continue

        for j in range(i+1, n):
            Zj = atomic_numbers[j]
            sym_j = Z_TO_SYMBOL.get(Zj)
            rj = COVALENT_RADII.get(sym_j)

            if rj is None:
                continue

            d = distance(i+1, j+1, coordinates)
            cutoff = scale * (ri + rj)

            if d <= cutoff:
                bonds.append((i+1, j+1, d))

    return bonds
