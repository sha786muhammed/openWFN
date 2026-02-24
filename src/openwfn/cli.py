# src/openwfn/cli.py

import argparse
import os
import subprocess
import shutil
import sys

from .fchk import read_fchk, parse_fchk_scalars, parse_fchk_arrays, print_atom_table  # type: ignore
from .geometry import (  # type: ignore
    distance,
    angle,
    dihedral,
    molecular_formula,
    center_of_mass,
    detect_bonds,
)
from . import commands as cmd  # type: ignore
from .xyz import write_xyz  # type: ignore
from .interactive import run_interactive  # type: ignore


# -------------------------------------------------
# Utilities
# -------------------------------------------------

def ensure_fchk(file):
    """Convert .chk → .fchk if necessary."""
    if file.endswith(".fchk"):
        return file

    if file.endswith(".chk"):
        if not shutil.which("formchk"):
            sys.exit("Error: 'formchk' not found in PATH.")

        out = file.replace(".chk", ".fchk")

        if not os.path.exists(out):
            print(f"Converting {file} → {out}")
            subprocess.run(["formchk", file, out], check=True)

        return out

    sys.exit("Error: input must be .chk or .fchk")


def load_data(filename):
    fchk_file = ensure_fchk(filename)
    lines = read_fchk(fchk_file)
    scalars = parse_fchk_scalars(lines)
    atomic_numbers, coordinates = parse_fchk_arrays(lines)
    return fchk_file, scalars, atomic_numbers, coordinates


# -------------------------------------------------
# Main CLI
# -------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        prog="openwfn",
        description="openWFN — Lightweight Wavefunction Geometry Toolkit"
    )

    parser.add_argument("file", help="Gaussian .chk or .fchk file")

    subparsers = parser.add_subparsers(dest="command")

    # summary (now the default view)
    subparsers.add_parser("summary", help="Show professional molecular summary")

    # info
    subparsers.add_parser("info", help="Show detailed FCHK metadata")

    # ... [rest of parsers remain same] ...
    # distance
    p_dist = subparsers.add_parser("dist", help="Distance between two atoms")
    p_dist.add_argument("i", type=int)
    p_dist.add_argument("j", type=int)

    # angle
    p_angle = subparsers.add_parser("angle", help="Bond angle i-j-k")
    p_angle.add_argument("i", type=int)
    p_angle.add_argument("j", type=int)
    p_angle.add_argument("k", type=int)

    # dihedral
    p_dih = subparsers.add_parser("dihedral", help="Dihedral i-j-k-l")
    p_dih.add_argument("i", type=int)
    p_dih.add_argument("j", type=int)
    p_dih.add_argument("k", type=int)
    p_dih.add_argument("l", type=int)

    # bonds
    subparsers.add_parser("bonds", help="Detect covalent bonds")

    # xyz
    p_xyz = subparsers.add_parser("xyz", help="Export XYZ file")
    p_xyz.add_argument("output", help="Output XYZ filename")

    # interactive
    subparsers.add_parser("interactive", help="Launch interactive menu mode")

    # graph
    subparsers.add_parser("graph", help="Show molecular graph components")

    # density
    p_dens = subparsers.add_parser("density", help="Compute electron density on a grid")
    p_dens.add_argument("--grid-size", default="40x40x40", help="Grid sizes (unused, uses spacing currently)")
    p_dens.add_argument("--export", required=True, help="Output VTK file path")

    # mo
    p_mo = subparsers.add_parser("mo", help="Compute MO on a grid")
    p_mo.add_argument("index", type=int, help="MO index")
    p_mo.add_argument("--export", required=True, help="Output VTK file path")

    args = parser.parse_args()

    # If no subcommand → default to interactive if it's a TTY, else summary
    if getattr(args, "command", None) is None:
        if sys.stdin.isatty():
            args.command = "interactive"  # type: ignore
        else:
            args.command = "summary"  # type: ignore

    filename = args.file
    try:
        fchk_file, scalars, atomic_numbers, coordinates = load_data(filename)
    except Exception as e:
        from . import utils  # type: ignore
        utils.print_error(str(e))
        return 1

    lines = read_fchk(fchk_file)

    # -----------------------------
    # Commands
    # -----------------------------

    if args.command == "summary": # type: ignore
        cmd.cmd_summary(scalars, atomic_numbers, coordinates)

    elif args.command == "info": # type: ignore
        cmd.cmd_info(scalars, atomic_numbers, coordinates)

    elif args.command == "dist": # type: ignore
        cmd.cmd_dist(args.i, args.j, coordinates)

    elif args.command == "angle": # type: ignore
        cmd.cmd_angle(args.i, args.j, args.k, coordinates)

    elif args.command == "dihedral": # type: ignore
        cmd.cmd_dihedral(args.i, args.j, args.k, args.l, coordinates)

    elif args.command == "bonds": # type: ignore
        cmd.cmd_bonds(atomic_numbers, coordinates)

    elif args.command == "graph": # type: ignore
        cmd.cmd_graph(atomic_numbers, coordinates)

    elif args.command == "density": # type: ignore
        cmd.cmd_density(filename, args.grid_size, args.export, lines, coordinates)

    elif args.command == "mo": # type: ignore
        cmd.cmd_mo(filename, args.index, args.export, lines, coordinates)

    elif args.command == "xyz": # type: ignore
        cmd.cmd_xyz(args.output, atomic_numbers, coordinates)

    elif args.command == "interactive": # type: ignore
        run_interactive(lines, fchk_file)

    return 0


if __name__ == "__main__":
    sys.exit(main())
