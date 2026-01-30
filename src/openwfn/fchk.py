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
