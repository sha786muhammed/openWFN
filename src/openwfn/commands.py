# src/openwfn/commands.py

from typing import List, Tuple, Dict, Any, Optional
from .geometry import (  # type: ignore
    distance,
    angle,
    dihedral,
    molecular_formula,
    center_of_mass,
    detect_bonds,
)
from .xyz import write_xyz  # type: ignore
from . import utils  # type: ignore


def cmd_summary(scalars: Dict[str, Any], atomic_numbers: List[int], coordinates: List[Tuple[float, float, float]]) -> None:
    """Print a professional molecular summary."""
    utils.print_header("Molecular Summary")
    
    formula = molecular_formula(atomic_numbers)
    com = center_of_mass(atomic_numbers, coordinates)
    bonds = detect_bonds(atomic_numbers, coordinates)
    
    # Basic info
    print(f"{utils.highlight('Formula:')}    {formula}")
    print(f"{utils.highlight('Atoms:')}      {len(atomic_numbers)}")
    print(f"{utils.highlight('Charge:')}     {scalars.get('Charge', 'N/A')}")
    print(f"{utils.highlight('Spin Mult:')}  {scalars.get('Multiplicity', 'N/A')}")
    print(f"{utils.highlight('COM (Å):')}    ({com[0]:.3f}, {com[1]:.3f}, {com[2]:.3f})")
    
    # Electronics
    if "Total Energy" in scalars:
        print(f"{utils.highlight('Energy:')}      {scalars['Total Energy']:.8f} a.u.")
    
    # Topology
    from .graph import build_graph  # type: ignore
    g = build_graph(len(atomic_numbers), bonds)
    comps = g.connected_components()
    
    print(f"{utils.highlight('Bonds:')}      {len(bonds)}")
    print(f"{utils.highlight('Fragments:')}  {len(comps)}")
    print()


def cmd_info(scalars: Dict[str, Any], atomic_numbers: List[int], coordinates: List[Tuple[float, float, float]]) -> None:
    """Print detailed molecular metadata."""
    utils.print_header("FCHK Metadata")
    
    if not scalars:
        print("No metadata found.")
        return

    # Filter out empty or common keys to make it cleaner
    for key, value in scalars.items():
        print(f"{key:<30}: {value}")
    print()


def cmd_dist(i: int, j: int, coordinates: List[Tuple[float, float, float]]) -> None:
    """Calculate and print distance between two atoms."""
    try:
        d = distance(i, j, coordinates)
        utils.print_header("Distance Calculation")
        print(f"Distance ({i} - {j}): {utils.highlight(f'{d:.6f}')} Å")
    except IndexError:
        utils.print_error(f"Atom index out of range (1 to {len(coordinates)})")


def cmd_angle(i: int, j: int, k: int, coordinates: List[Tuple[float, float, float]]) -> None:
    """Calculate and print bond angle."""
    try:
        a = angle(i, j, k, coordinates)
        utils.print_header("Angle Calculation")
        print(f"Angle ({i}-{j}-{k}): {utils.highlight(f'{a:.3f}')}°")
    except IndexError:
        utils.print_error(f"Atom index out of range")


def cmd_dihedral(i: int, j: int, k: int, l: int, coordinates: List[Tuple[float, float, float]]) -> None:
    """Calculate and print dihedral angle."""
    try:
        d = dihedral(i, j, k, l, coordinates)
        utils.print_header("Dihedral Calculation")
        print(f"Dihedral ({i}-{j}-{k}-{l}): {utils.highlight(f'{d:.3f}')}°")
    except IndexError:
        utils.print_error(f"Atom index out of range")


def cmd_bonds(atomic_numbers: List[int], coordinates: List[Tuple[float, float, float]]) -> None:
    """Detect and print covalent bonds with formatting."""
    from .constants import Z_TO_SYMBOL  # type: ignore
    
    bonds = detect_bonds(atomic_numbers, coordinates)
    utils.print_header("Covalent Bond Detection")
    
    if not bonds:
        print("No bonds detected within standard covalent radii.")
        return

    utils.print_table_header([("Atom I", 10), ("Atom J", 10), ("Dist (Å)", 10)])
    for i, j, dist in bonds:
        sym_i = Z_TO_SYMBOL.get(atomic_numbers[i-1], "X")
        sym_j = Z_TO_SYMBOL.get(atomic_numbers[j-1], "X")
        utils.print_table_row([
            (f"{i}-{sym_i}", 10),
            (f"{j}-{sym_j}", 10),
            (f"{dist:.4f}", 10)
        ])
    print(f"\nTotal: {utils.highlight(str(len(bonds)))} bonds detected.")


def cmd_xyz(output_filename: str, atomic_numbers: List[int], coordinates: List[Tuple[float, float, float]]) -> None:
    """Export coordinates to an XYZ file."""
    write_xyz(output_filename, atomic_numbers, coordinates)
    utils.print_success(f"XYZ file successfully exported to: {output_filename}")


def cmd_density(filename: str, grid_size: str, output: str, lines: List[str], coordinates: List[Tuple[float, float, float]]) -> None:
    """Calculate electron density on a grid and export to VTK."""
    from .fchk import parse_fchk_density  # type: ignore
    from .grid import make_bounding_box_grid  # type: ignore
    from .density import compute_density  # type: ignore
    from .export import export_vtk  # type: ignore
    import numpy as np
    
    density_data = parse_fchk_density(lines)
    if not density_data or "total_scf_density" not in density_data:
        utils.print_error("Total SCF Density not found in FCHK.")
        return
        
    P_mu_nu = density_data["total_scf_density"]
    
    utils.print_header("Electron Density Computation")
    print(f"Generating grid for {len(coordinates)} atoms...")
    
    # Simple grid sizing parsing (e.g., 40x40x40 parsing stub or use spacing)
    points, shape = make_bounding_box_grid(coordinates, margin=3.0, spacing=0.2)
    rho = compute_density(points, np.array(P_mu_nu))
    
    export_vtk(output, points, shape, rho, data_name="SCF_Density")
    utils.print_success(f"Grid exported: {points.shape[0]} points captured in {output}")


def cmd_mo(filename: str, index: int, output: str, lines: List[str], coordinates: List[Tuple[float, float, float]]) -> None:
    """Evaluate a specific molecular orbital on a grid."""
    utils.print_header("MO Evaluation")
    utils.print_warning("Molecular Orbital evaluation is currently a stub.")


def cmd_graph(atomic_numbers: List[int], coordinates: List[Tuple[float, float, float]]) -> None:
    """Build and display molecular graph fragments."""
    from .graph import build_graph  # type: ignore
    from .geometry import detect_bonds  # type: ignore
    from .constants import Z_TO_SYMBOL  # type: ignore
    
    bonds = detect_bonds(atomic_numbers, coordinates)
    g = build_graph(len(atomic_numbers), bonds)
    comps = g.connected_components()
    
    utils.print_header("Molecular Topology & Fragments")
    
    for i, nodes in enumerate(comps, 1):
        # Determine formula for this fragment
        comp_atomic_nums = [atomic_numbers[n-1] for n in nodes]
        formula = molecular_formula(comp_atomic_nums)
        
        print(f"Fragment {i}: {utils.highlight(formula)}")
        print(f"  Atoms ({len(nodes)}): {', '.join(map(str, nodes))}")
    print()
