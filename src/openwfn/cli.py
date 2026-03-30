# src/openwfn/cli.py

import argparse
import os
import shutil
import subprocess
import sys
from typing import Any

from .fchk import parse_fchk_arrays, parse_fchk_scalars, read_fchk  # type: ignore
from . import commands as cmd  # type: ignore
from .interactive import run_interactive  # type: ignore
from . import utils  # type: ignore


# -------------------------------------------------
# Utilities
# -------------------------------------------------

def ensure_fchk(file: str) -> str:
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


def load_data(filename: str) -> tuple[str, dict[str, Any], list[int], list[tuple[float, float, float]]]:
    fchk_file = ensure_fchk(filename)
    lines = read_fchk(fchk_file)
    scalars = parse_fchk_scalars(lines)
    atomic_numbers, coordinates = parse_fchk_arrays(lines)
    return fchk_file, scalars, atomic_numbers, coordinates


# -------------------------------------------------
# Main CLI
# -------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="openwfn",
        description=(
            "openWFN — Lightweight Wavefunction Geometry Toolkit. "
            "Geometry analysis commands are stable; 'density' and 'mo' are experimental "
            "and currently unavailable for production use."
        )
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
    p_dens = subparsers.add_parser(
        "density",
        help="Experimental: electron-density export pathway (currently unavailable)"
    )
    p_dens.add_argument(
        "--grid-size",
        default="40x40x40",
        help="Requested grid size placeholder (currently ignored; spacing-based grid is used)"
    )
    p_dens.add_argument("--export", required=True, help="Output VTK file path")

    # mo
    p_mo = subparsers.add_parser(
        "mo",
        help="Experimental: molecular-orbital export pathway (currently unavailable)"
    )
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
        utils.print_error(str(e))
        return 1

    lines = read_fchk(fchk_file)

    # -----------------------------
    # Commands
    # -----------------------------

    try:
        if args.command == "summary": # type: ignore
            return cmd.cmd_summary(scalars, atomic_numbers, coordinates)

        if args.command == "info": # type: ignore
            return cmd.cmd_info(scalars, atomic_numbers, coordinates)

        if args.command == "dist": # type: ignore
            return cmd.cmd_dist(args.i, args.j, coordinates)

        if args.command == "angle": # type: ignore
            return cmd.cmd_angle(args.i, args.j, args.k, coordinates)

        if args.command == "dihedral": # type: ignore
            return cmd.cmd_dihedral(args.i, args.j, args.k, args.l, coordinates)

        if args.command == "bonds": # type: ignore
            return cmd.cmd_bonds(atomic_numbers, coordinates)

        if args.command == "graph": # type: ignore
            return cmd.cmd_graph(atomic_numbers, coordinates)

        if args.command == "density": # type: ignore
            return cmd.cmd_density(filename, args.grid_size, args.export, lines, coordinates)

        if args.command == "mo": # type: ignore
            return cmd.cmd_mo(filename, args.index, args.export, lines, coordinates)

        if args.command == "xyz": # type: ignore
            return cmd.cmd_xyz(args.output, atomic_numbers, coordinates)

        if args.command == "interactive": # type: ignore
            run_interactive(lines, fchk_file)
            return 0
    except Exception as e:
        utils.print_error(str(e))
        return 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
