# src/openwfn/cli.py

import argparse
import os
import subprocess
import shutil
import sys

from openwfn.fchk import read_fchk, parse_fchk_scalars, parse_fchk_arrays, print_atom_table
from openwfn.geometry import (
    distance,
    angle,
    dihedral,
    molecular_formula,
    center_of_mass,
    detect_bonds,
)
import openwfn.commands as cmd
from openwfn.xyz import write_xyz
from openwfn.interactive import run_interactive


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

    # info
    subparsers.add_parser("info", help="Show molecular information")

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
    subparsers.add_parser("interactive", help="Launch interactive mode")

    args = parser.parse_args()

    # If no subcommand → default to interactive
    if args.command is None:
        args.command = "interactive"

    filename = args.file
    fchk_file, scalars, atomic_numbers, coordinates = load_data(filename)

    # -----------------------------
    # Commands
    # -----------------------------

    if args.command == "info":
        cmd.cmd_info(scalars, atomic_numbers, coordinates)

    elif args.command == "dist":
        cmd.cmd_dist(args.i, args.j, coordinates)

    elif args.command == "angle":
        cmd.cmd_angle(args.i, args.j, args.k, coordinates)

    elif args.command == "dihedral":
        cmd.cmd_dihedral(args.i, args.j, args.k, args.l, coordinates)

    elif args.command == "bonds":
        cmd.cmd_bonds(atomic_numbers, coordinates)

    elif args.command == "xyz":
        cmd.cmd_xyz(args.output, atomic_numbers, coordinates)

    elif args.command == "interactive":
        lines = read_fchk(fchk_file)
        run_interactive(lines, fchk_file)

    return 0


if __name__ == "__main__":
    sys.exit(main())
