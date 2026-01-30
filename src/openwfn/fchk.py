# Minimal periodic table (extend later)
Z_TO_SYMBOL = {
    1: "H",
    6: "C",
    7: "N",
    8: "O",
    9: "F",
    15: "P",
    16: "S",
    17: "Cl",
}


def read_fchk(filepath):
    """
    Read a Gaussian formatted checkpoint (.fchk) file
    and return all lines as a list of strings.
    """
    with open(filepath, "r") as f:
        lines = f.readlines()
    return lines


def parse_fchk_scalars(lines):
    """
    Parse scalar integer fields from fchk lines.
    Returns a dictionary with selected scalar values.
    """
    # Fields we want to extract (exact fchk names)
    scalar_fields = {
        "Charge",
        "Multiplicity",
        "Number of atoms",
        "Number of alpha electrons",
        "Number of beta electrons",
    }

    data = {}

    for line in lines:
        # Split line into words
        parts = line.strip().split()

        # Skip empty or very short lines
        if len(parts) < 3:
            continue

        # Field name may contain spaces → reconstruct it
        field_name = " ".join(parts[:-2])
        field_type = parts[-2]
        field_value = parts[-1]

        # We only care about integer scalar fields
        if field_name in scalar_fields and field_type == "I":
            try:
                data[field_name] = int(field_value)
            except ValueError:
                pass  # Ignore malformed values

    return data

import re


def parse_fchk_arrays(lines):
    """
    Parse selected array fields from fchk lines.
    Returns atomic numbers and Cartesian coordinates.
    """
    atomic_numbers = []
    coordinates = []

    i = 0
    n_lines = len(lines)

    while i < n_lines:
        line = lines[i].rstrip()

        # ---------- Atomic numbers ----------
        if line.startswith("Atomic numbers"):
            match = re.search(r"N\s*=\s*(\d+)", line)
            if not match:
                raise ValueError("Could not parse N for Atomic numbers")

            n = int(match.group(1))
            values = []

            i += 1
            while i < n_lines and len(values) < n:
                for tok in lines[i].split():
                    if tok.isdigit():
                        values.append(int(tok))
                i += 1

            atomic_numbers = values[:n]
            continue

        # ---------- Cartesian coordinates ----------
        if line.startswith("Current cartesian coordinates"):
            match = re.search(r"N\s*=\s*(\d+)", line)
            if not match:
                raise ValueError("Could not parse N for Cartesian coordinates")

            n = int(match.group(1))
            values = []

            i += 1
            while i < n_lines and len(values) < n:
                for tok in lines[i].split():
                    try:
                        values.append(float(tok))
                    except ValueError:
                        pass
                i += 1

            coords = values[:n]
            coordinates = [
                tuple(coords[j:j + 3]) for j in range(0, len(coords), 3)
            ]
            continue

        i += 1

    return atomic_numbers, coordinates

def print_atom_table(atomic_numbers, coordinates):
    """
    Print atom index table with element symbols and coordinates.
    """
    print("Atom index table")
    print("----------------")

    for i, (Z, (x, y, z)) in enumerate(zip(atomic_numbers, coordinates), start=1):
        symbol = Z_TO_SYMBOL.get(Z, f"Z{Z}")
        print(f"{i:3d}  {symbol:2s}  {x:12.6f}  {y:12.6f}  {z:12.6f}")

import math


def distance(atom_i, atom_j, coordinates):
    """
    Compute distance between atom_i and atom_j (1-based indices).
    Returns distance in Angstrom.
    """
    # Convert to 0-based indices
    i = atom_i - 1
    j = atom_j - 1

    xi, yi, zi = coordinates[i]
    xj, yj, zj = coordinates[j]

    dx = xi - xj
    dy = yi - yj
    dz = zi - zj

    return math.sqrt(dx*dx + dy*dy + dz*dz)

def angle(atom_i, atom_j, atom_k, coordinates):
    """
    Compute bond angle i–j–k (in degrees).
    Atom indices are 1-based.
    """
    import math

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
    cos_theta = max(-1.0, min(1.0, cos_theta))  # numerical safety

    theta = math.degrees(math.acos(cos_theta))
    return theta

def dihedral(atom_i, atom_j, atom_k, atom_l, coordinates):
    """
    Compute dihedral angle i–j–k–l (degrees).
    """
    import math

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

    angle = math.degrees(math.atan2(y, x))
    return angle


def write_xyz(filename, atomic_numbers, coordinates):
    """
    Write XYZ file.
    """
    symbols = [Z_TO_SYMBOL.get(Z, "X") for Z in atomic_numbers]

    with open(filename, "w") as f:
        f.write(f"{len(symbols)}\n")
        f.write("Generated by openWFN\n")
        for sym, (x, y, z) in zip(symbols, coordinates):
            f.write(f"{sym:2s} {x:12.6f} {y:12.6f} {z:12.6f}\n")




