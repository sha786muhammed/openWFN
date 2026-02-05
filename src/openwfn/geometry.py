# src/openwfn/geometry.py

import math
from collections import Counter

# -------------------------------------------------
# Geometry calculations
# -------------------------------------------------

def distance(atom_i, atom_j, coordinates):
    i, j = atom_i - 1, atom_j - 1

    xi, yi, zi = coordinates[i]
    xj, yj, zj = coordinates[j]

    dx, dy, dz = xi-xj, yi-yj, zi-zj
    return math.sqrt(dx*dx + dy*dy + dz*dz)


def angle(atom_i, atom_j, atom_k, coordinates):
    i, j, k = atom_i-1, atom_j-1, atom_k-1

    xi, yi, zi = coordinates[i]
    xj, yj, zj = coordinates[j]
    xk, yk, zk = coordinates[k]

    v1 = (xi-xj, yi-yj, zi-zj)
    v2 = (xk-xj, yk-yj, zk-zj)

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

ATOMIC_MASS = {
    1: 1.008, 6: 12.011, 7: 14.007, 8: 15.999,
    9: 18.998, 15: 30.974, 16: 32.06, 17: 35.45
}

Z_TO_SYMBOL = {
    1:"H", 6:"C", 7:"N", 8:"O", 9:"F",
    15:"P", 16:"S", 17:"Cl"
}


def molecular_formula(atomic_numbers):
    counts = Counter(atomic_numbers)

    parts = []
    for Z in sorted(counts):
        sym = Z_TO_SYMBOL.get(Z, f"Z{Z}")
        n = counts[Z]
        parts.append(f"{sym}{n if n>1 else ''}")

    return "".join(parts)


def center_of_mass(atomic_numbers, coordinates):
    total = 0.0
    cx = cy = cz = 0.0

    for Z, (x, y, z) in zip(atomic_numbers, coordinates):
        m = ATOMIC_MASS.get(Z, 12.0)
        total += m
        cx += m*x
        cy += m*y
        cz += m*z

    return cx/total, cy/total, cz/total
