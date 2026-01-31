# src/openwfn/geometry.py

import math


def distance(atom_i, atom_j, coordinates):
    i = atom_i - 1
    j = atom_j - 1

    xi, yi, zi = coordinates[i]
    xj, yj, zj = coordinates[j]

    dx = xi - xj
    dy = yi - yj
    dz = zi - zj

    return math.sqrt(dx*dx + dy*dy + dz*dz)


def angle(atom_i, atom_j, atom_k, coordinates):
    i = atom_i - 1
    j = atom_j - 1
    k = atom_k - 1

    xi, yi, zi = coordinates[i]
    xj, yj, zj = coordinates[j]
    xk, yk, zk = coordinates[k]

    v1 = (xi - xj, yi - yj, zi - zj)
    v2 = (xk - xj, yk - yj, zk - zj)

    dot = sum(a*b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a*a for a in v1))
    norm2 = math.sqrt(sum(a*a for a in v2))

    cos_theta = dot / (norm1 * norm2)
    cos_theta = max(-1.0, min(1.0, cos_theta))

    return math.degrees(math.acos(cos_theta))


def dihedral(atom_i, atom_j, atom_k, atom_l, coordinates):
    i = atom_i - 1
    j = atom_j - 1
    k = atom_k - 1
    l = atom_l - 1

    def vec(a, b):
        return tuple(b[i] - a[i] for i in range(3))

    def cross(u, v):
        return (
            u[1]*v[2] - u[2]*v[1],
            u[2]*v[0] - u[0]*v[2],
            u[0]*v[1] - u[1]*v[0],
        )

    def dot(u, v):
        return sum(u[i]*v[i] for i in range(3))

    def norm(v):
        return math.sqrt(dot(v, v))

    r1, r2, r3, r4 = coordinates[i], coordinates[j], coordinates[k], coordinates[l]

    b1 = vec(r2, r1)
    b2 = vec(r2, r3)
    b3 = vec(r4, r3)

    n1 = cross(b1, b2)
    n2 = cross(b2, b3)

    m1 = cross(n1, b2)

    x = dot(n1, n2)
    y = dot(m1, n2) / norm(b2)

    return math.degrees(math.atan2(y, x))
