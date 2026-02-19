# src/openwfn/commands.py

from typing import List, Tuple, Dict, Any, Optional
from openwfn.geometry import (
    distance,
    angle,
    dihedral,
    molecular_formula,
    center_of_mass,
    detect_bonds,
)
from openwfn.xyz import write_xyz


def cmd_info(scalars: Dict[str, int], atomic_numbers: List[int], coordinates: List[Tuple[float, float, float]]) -> None:
    """Print molecular information."""
    formula = molecular_formula(atomic_numbers)
    com = center_of_mass(atomic_numbers, coordinates)

    print("Molecular Information")
    print("---------------------")
    print(f"Atoms: {len(atomic_numbers)}")
    print(f"Formula: {formula}")
    print(f"Charge: {scalars.get('Charge')}")
    print(f"Multiplicity: {scalars.get('Multiplicity')}")
    print(f"Center of mass: ({com[0]:.3f}, {com[1]:.3f}, {com[2]:.3f})")


def cmd_dist(i: int, j: int, coordinates: List[Tuple[float, float, float]]) -> None:
    """Calculate and print distance between two atoms."""
    d = distance(i, j, coordinates)
    print(f"{d:.6f} Å")


def cmd_angle(i: int, j: int, k: int, coordinates: List[Tuple[float, float, float]]) -> None:
    """Calculate and print bond angle."""
    a = angle(i, j, k, coordinates)
    print(f"{a:.3f}°")


def cmd_dihedral(i: int, j: int, k: int, l: int, coordinates: List[Tuple[float, float, float]]) -> None:
    """Calculate and print dihedral angle."""
    d = dihedral(i, j, k, l, coordinates)
    print(f"{d:.3f}°")


def cmd_bonds(atomic_numbers: List[int], coordinates: List[Tuple[float, float, float]]) -> None:
    """Detect and print covalent bonds."""
    bonds = detect_bonds(atomic_numbers, coordinates)
    print("Detected bonds (Å)")
    print("------------------")
    if not bonds:
        print("No bonds detected.")
    for i, j, dist in bonds:
        print(f"{i}-{j}: {dist:.3f}")


def cmd_xyz(output_filename: str, atomic_numbers: List[int], coordinates: List[Tuple[float, float, float]]) -> None:
    """Export coordinates to an XYZ file."""
    write_xyz(output_filename, atomic_numbers, coordinates)
    print(f"XYZ file written to {output_filename}")
