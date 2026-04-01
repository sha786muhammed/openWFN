# src/openwfn/commands.py

from typing import Any
import webbrowser
from pathlib import Path

import numpy as np  # type: ignore

from .export import export_molecule_viewer  # type: ignore
from .geometry import (  # type: ignore
    angle,
    center_of_mass,
    detect_bonds,
    dihedral,
    distance,
    molecular_formula,
)
from .xyz import write_xyz  # type: ignore
from . import utils  # type: ignore


def cmd_summary(
    scalars: dict[str, Any],
    atomic_numbers: list[int],
    coordinates: list[tuple[float, float, float]],
) -> int:
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
    return 0


def cmd_info(
    scalars: dict[str, Any],
    atomic_numbers: list[int],
    coordinates: list[tuple[float, float, float]],
) -> int:
    """Print detailed molecular metadata."""
    del atomic_numbers, coordinates
    utils.print_header("FCHK Metadata")
    
    if not scalars:
        print("No metadata found.")
        return 0

    # Filter out empty or common keys to make it cleaner
    for key, value in scalars.items():
        print(f"{key:<30}: {value}")
    print()
    return 0


def cmd_dist(i: int, j: int, coordinates: list[tuple[float, float, float]]) -> int:
    """Calculate and print distance between two atoms."""
    try:
        d = distance(i, j, coordinates)
        utils.print_header("Distance Calculation")
        print(f"Distance ({i} - {j}): {utils.highlight(f'{d:.6f}')} Å")
        return 0
    except (IndexError, ValueError) as e:
        utils.print_error(str(e))
        return 1


def cmd_angle(i: int, j: int, k: int, coordinates: list[tuple[float, float, float]]) -> int:
    """Calculate and print bond angle."""
    try:
        a = angle(i, j, k, coordinates)
        utils.print_header("Angle Calculation")
        print(f"Angle ({i}-{j}-{k}): {utils.highlight(f'{a:.3f}')}°")
        return 0
    except (IndexError, ValueError) as e:
        utils.print_error(str(e))
        return 1


def cmd_dihedral(i: int, j: int, k: int, l: int, coordinates: list[tuple[float, float, float]]) -> int:
    """Calculate and print dihedral angle."""
    try:
        d = dihedral(i, j, k, l, coordinates)
        utils.print_header("Dihedral Calculation")
        print(f"Dihedral ({i}-{j}-{k}-{l}): {utils.highlight(f'{d:.3f}')}°")
        return 0
    except (IndexError, ValueError) as e:
        utils.print_error(str(e))
        return 1


def cmd_bonds(atomic_numbers: list[int], coordinates: list[tuple[float, float, float]]) -> int:
    """Detect and print covalent bonds with formatting."""
    from .constants import Z_TO_SYMBOL  # type: ignore
    
    bonds = detect_bonds(atomic_numbers, coordinates)
    utils.print_header("Covalent Bond Detection")
    
    if not bonds:
        print("No bonds detected within standard covalent radii.")
        return 0

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
    return 0


def cmd_xyz(output_filename: str, atomic_numbers: list[int], coordinates: list[tuple[float, float, float]]) -> int:
    """Export coordinates to an XYZ file."""
    write_xyz(output_filename, atomic_numbers, coordinates)
    utils.print_success(f"XYZ file successfully exported to: {output_filename}")
    return 0


def cmd_view(
    output_filename: str | None,
    atomic_numbers: list[int],
    coordinates: list[tuple[float, float, float]],
    open_browser: bool = False,
    show_labels: bool = True,
    style: str = "ballstick",
) -> int:
    """Export and optionally open a standalone browser-based molecule viewer."""
    output_path = Path(output_filename) if output_filename is not None else Path("openwfn_viewer.html")

    export_molecule_viewer(
        output_path,
        atomic_numbers,
        coordinates,
        show_labels=show_labels,
        style=style,
    )
    utils.print_success(f"Standalone molecule viewer exported to: {output_path}")
    if open_browser:
        opened = webbrowser.open(output_path.resolve().as_uri())
        if opened:
            utils.print_success("Viewer opened in your default browser.")
        else:
            utils.print_warning("Viewer file was created, but automatic browser opening was not available.")
    else:
        print("Use this HTML file directly or share it for download; no extra viewer assets are required.")
    return 0


def cmd_density(
    filename: str,
    grid_size: str,
    output: str,
    lines: list[str],
    coordinates: list[tuple[float, float, float]],
) -> int:
    """Calculate electron density on a grid and export to VTK."""
    del filename, grid_size
    from .fchk import parse_fchk_density  # type: ignore
    from .grid import make_bounding_box_grid  # type: ignore
    from .density import compute_density  # type: ignore
    from .export import export_vtk  # type: ignore

    density_data = parse_fchk_density(lines)
    if not density_data or "total_scf_density" not in density_data:
        utils.print_error("Total SCF Density not found in FCHK.")
        return 1
        
    P_mu_nu = density_data["total_scf_density"]
    
    utils.print_header("Electron Density Computation")
    print(f"Generating grid for {len(coordinates)} atoms...")
    
    # Simple grid sizing parsing (e.g., 40x40x40 parsing stub or use spacing)
    points, shape = make_bounding_box_grid(coordinates, margin=3.0, spacing=0.2)
    try:
        rho = compute_density(points, np.array(P_mu_nu))
    except NotImplementedError as e:
        utils.print_error(str(e))
        return 1
    
    export_vtk(output, points, shape, rho, data_name="SCF_Density")
    utils.print_success(f"Grid exported: {points.shape[0]} points captured in {output}")
    return 0


def cmd_mo(
    filename: str,
    index: int,
    output: str,
    lines: list[str],
    coordinates: list[tuple[float, float, float]],
) -> int:
    """Evaluate a specific molecular orbital on a grid."""
    del filename, index, output, lines, coordinates
    utils.print_error(
        "Molecular orbital grid evaluation is not implemented yet. "
        "The 'mo' command is currently unavailable."
    )
    return 1


def cmd_graph(atomic_numbers: list[int], coordinates: list[tuple[float, float, float]]) -> int:
    """Build and display molecular graph fragments."""
    from .graph import build_graph  # type: ignore

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
    return 0
