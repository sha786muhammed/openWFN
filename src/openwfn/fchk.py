# src/openwfn/fchk.py

import re
from typing import Any

from .constants import Z_TO_SYMBOL, BOHR_TO_ANGSTROM  # type: ignore


def read_fchk(filepath: str) -> list[str]:
    """Read .fchk file and return lines."""
    with open(filepath, "r") as f:
        return f.readlines()


def parse_fchk_scalars(lines: list[str]) -> dict[str, Any]:
    """Parse scalar integer and real values from FCHK lines."""
    data: dict[str, Any] = {}

    for line in lines:
        # FCHK defines scalars as "Key  Type  Value"
        # Type is usually 'I' (integer) or 'R' (real)
        # We use regex to match the pattern: Key <whitespace> Type <whitespace> Value
        match = re.search(r"^(.*?)\s+([IR])\s+(.*)$", line)
        if match:
            key = match.group(1).strip()
            type_char = match.group(2)
            value = match.group(3).strip()
            
            if type_char == "I":
                try:
                    data[key] = int(value)
                except ValueError:
                    pass
            elif type_char == "R":
                try:
                    data[key] = float(value)
                except ValueError:
                    pass

    return data


def _get_array(lines: list[str], keyword: str, dtype: type = float) -> list[Any]:
    """
    Helper to find and parse an array from FCHK lines.
    Returns an empty list if not found.
    """
    data: list[Any] = []
    idx = 0
    
    # Simple linear scan suitable for small files. 
    # For very large files, a single pass parser structure would be better.
    while idx < len(lines):
        line = lines[idx].rstrip()
        if line.startswith(keyword):
            # Parse N=...
            match = re.search(r"N\s*=\s*(\d+)", line)
            if match:
                n = int(match.group(1))
                idx += 1

                while len(data) < n and idx < len(lines):
                    # FCHK arrays are space-separated, sometimes fixed width
                    # Splitting by whitespace usually works for standard files
                    row_vals = lines[idx].split()
                    for x in row_vals:
                        try:
                            data.append(dtype(x))
                        except ValueError:
                            pass
                    idx += 1

                return data
        idx += 1

    return data


def parse_fchk_arrays(lines: list[str]) -> tuple[list[int], list[tuple[float, float, float]]]:
    """
    Parse atomic numbers and coordinates from FCHK lines.
    Coordinates are converted from Bohr to Angstroms.
    """
    atomic_numbers = _get_array(lines, "Atomic numbers", int)
    raw_coords = _get_array(lines, "Current cartesian coordinates", float)
    if raw_coords and len(raw_coords) % 3 != 0:
        raise ValueError(
            "Malformed FCHK coordinates: expected a multiple of 3 values "
            f"(got {len(raw_coords)})."
        )

    coordinates = []
    if raw_coords:
        coordinates = [
            (
                raw_coords[j]   * BOHR_TO_ANGSTROM,
                raw_coords[j+1] * BOHR_TO_ANGSTROM,
                raw_coords[j+2] * BOHR_TO_ANGSTROM
            )
            for j in range(0, len(raw_coords), 3)
        ]

    return atomic_numbers, coordinates


def parse_fchk_basis(lines: list[str]) -> dict[str, list[Any]]:
    """
    Parse Basis Set information.
    """
    basis_data: dict[str, list[Any]] = {}
    basis_data["shell_types"] = _get_array(lines, "Shell types", int)
    basis_data["primitives_per_shell"] = _get_array(lines, "Number of primitives per shell", int)
    basis_data["shell_to_atom"] = _get_array(lines, "Shell to atom map", int)
    basis_data["primitive_exponents"] = _get_array(lines, "Primitive exponents", float)
    basis_data["contraction_coeffs"] = _get_array(lines, "Contraction coefficients", float)
    
    # Uncontracted P shells often have separate coefficients for s and p if SP shell
    # But FCHK stores SP as shell type -1 or similar (check Gaussian specs)
    # usually "P(S=P) Contraction coefficients" if present
    p_coeffs = _get_array(lines, "P(S=P) Contraction coefficients", float)
    if p_coeffs:
        basis_data["p_contraction_coeffs"] = p_coeffs
        
    return basis_data


def parse_fchk_mos(lines: list[str]) -> dict[str, list[float]]:
    """
    Parse Molecular Orbital (MO) energies and coefficients.
    """
    mo_data: dict[str, list[float]] = {}
    mo_data["alpha_energies"] = _get_array(lines, "Alpha MO energies", float)
    mo_data["alpha_coeffs"] = _get_array(lines, "Alpha MO coefficients", float)
    
    # Open shell
    beta_energies = _get_array(lines, "Beta MO energies", float)
    if beta_energies:
        mo_data["beta_energies"] = beta_energies
        mo_data["beta_coeffs"] = _get_array(lines, "Beta MO coefficients", float)
        
    return mo_data


def parse_fchk_density(lines: list[str]) -> dict[str, list[float]]:
    """Parse Density matrices."""
    density_data: dict[str, list[float]] = {}
    density_data["total_scf_density"] = _get_array(lines, "Total SCF Density", float)
    
    # Open shell density matrices
    spin_density = _get_array(lines, "Spin SCF Density", float)
    if spin_density:
        density_data["spin_scf_density"] = spin_density
        
    return density_data


def print_atom_table(atomic_numbers: list[int], coordinates: list[tuple[float, float, float]]) -> None:
    """Print a formatted table of atomic coordinates."""
    print("Atom index table")
    print("----------------")

    for i, (Z, (x, y, z)) in enumerate(zip(atomic_numbers, coordinates), start=1):
        symbol = Z_TO_SYMBOL.get(Z, f"Z{Z}")
        print(f"{i:3d}  {symbol:2s}  {x:12.6f}  {y:12.6f}  {z:12.6f}")
