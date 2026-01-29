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

