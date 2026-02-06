# src/openwfn/fchk.py

import re
from openwfn.constants import Z_TO_SYMBOL, BOHR_TO_ANGSTROM


def read_fchk(filepath):
    with open(filepath, "r") as f:
        return f.readlines()


def parse_fchk_scalars(lines):
    wanted = {
        "Charge",
        "Multiplicity",
        "Number of atoms",
        "Number of alpha electrons",
        "Number of beta electrons",
    }

    data = {}

    for line in lines:
        parts = line.strip().split()
        if len(parts) < 3:
            continue

        name = " ".join(parts[:-2])
        ftype = parts[-2]
        value = parts[-1]

        if name in wanted and ftype == "I":
            try:
                data[name] = int(value)
            except ValueError:
                pass

    return data


def parse_fchk_arrays(lines):
    atomic_numbers = []
    coordinates = []

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        if line.startswith("Atomic numbers"):
            n = int(re.search(r"N\s*=\s*(\d+)", line).group(1))
            values = []
            i += 1
            while len(values) < n:
                values.extend(int(x) for x in lines[i].split() if x.isdigit())
                i += 1
            atomic_numbers = values[:n]
            continue

        if line.startswith("Current cartesian coordinates"):
            n = int(re.search(r"N\s*=\s*(\d+)", line).group(1))
            values = []
            i += 1
            while len(values) < n:
                for x in lines[i].split():
                    try:
                        values.append(float(x))
                    except ValueError:
                        pass
                i += 1

            coords = values[:n]     

            coordinates = [
                (
                    coords[j]   * BOHR_TO_ANGSTROM,
                    coords[j+1] * BOHR_TO_ANGSTROM,
                    coords[j+2] * BOHR_TO_ANGSTROM
                )
                for j in range(0, len(coords), 3)
            ]
            continue

        i += 1

    return atomic_numbers, coordinates


def print_atom_table(atomic_numbers, coordinates):
    print("Atom index table")
    print("----------------")

    for i, (Z, (x, y, z)) in enumerate(zip(atomic_numbers, coordinates), start=1):
        symbol = Z_TO_SYMBOL.get(Z, f"Z{Z}")
        print(f"{i:3d}  {symbol:2s}  {x:12.6f}  {y:12.6f}  {z:12.6f}")
