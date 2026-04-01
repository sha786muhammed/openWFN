# src/openwfn/cli.py

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .fchk import parse_fchk_arrays, parse_fchk_scalars, read_fchk  # type: ignore
from . import commands as cmd  # type: ignore
from .interactive import run_interactive  # type: ignore
from . import utils  # type: ignore


# -------------------------------------------------
# Utilities
# -------------------------------------------------

def convert_chk_to_fchk(file: str, output: str | None = None, *, quiet: bool = False) -> str:
    """Convert a Gaussian .chk file into a .fchk file."""
    if not file.endswith(".chk"):
        raise ValueError("Checkpoint conversion requires a Gaussian `.chk` input file.")

    if not shutil.which("formchk"):
        raise RuntimeError(
            "Gaussian checkpoint conversion requires `formchk`, but it was not found in your PATH. "
            "Add Gaussian utilities to PATH or convert the file manually with "
            "`formchk input.chk output.fchk`."
        )

    output_path = output or str(Path(file).with_suffix(".fchk"))

    if not os.path.exists(output_path):
        if not quiet:
            print(f"Converting Gaussian checkpoint: {file} -> {output_path}")
        subprocess.run(["formchk", file, output_path], check=True)
        if not quiet:
            utils.print_success(f"Formatted checkpoint written beside the input file: {output_path}")
    elif not quiet:
        utils.print_success(f"Reusing existing formatted checkpoint: {output_path}")

    return output_path


def ensure_fchk(file: str) -> str:
    """Convert .chk -> .fchk if necessary."""
    if file.endswith(".fchk"):
        return file

    if file.endswith(".chk"):
        return convert_chk_to_fchk(file)

    sys.exit("Input must be a Gaussian `.chk` or `.fchk` file.")


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

    subparsers = parser.add_subparsers(
        dest="command",
        metavar="{summary,info,dist,angle,dihedral,bonds,xyz,formchk,view,interactive,graph}",
    )

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

    # formchk
    p_formchk = subparsers.add_parser(
        "formchk",
        help="Convert a Gaussian checkpoint (.chk) file into a formatted checkpoint (.fchk)",
    )
    p_formchk.add_argument(
        "output",
        nargs="?",
        help="Optional output .fchk path (defaults to the input name with .fchk)",
    )

    # view
    p_view = subparsers.add_parser("view", help="Export a standalone local HTML molecule viewer with atom labels")
    p_view.add_argument("--save", help="Optional HTML output path")
    p_view.add_argument("--open", action="store_true", help="Open the exported viewer in your default browser")
    p_view.add_argument("--no-open", action="store_true", help=argparse.SUPPRESS)
    p_view.add_argument("--no-labels", action="store_true", help="Hide atom labels in the viewer")
    p_view.add_argument(
        "--style",
        choices=["ballstick", "stick"],
        default="ballstick",
        help="Viewer rendering style",
    )

    # interactive
    subparsers.add_parser("interactive", help="Launch interactive menu mode")

    # graph
    subparsers.add_parser("graph", help="Show molecular graph components")

    # density
    p_dens = subparsers.add_parser(
        "density",
        help=argparse.SUPPRESS,
        description="Experimental developer preview: electron-density export pathway.",
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
        help=argparse.SUPPRESS,
        description="Experimental developer preview: molecular-orbital export pathway.",
    )
    p_mo.add_argument("index", type=int, help="MO index")
    p_mo.add_argument("--export", required=True, help="Output VTK file path")

    # Keep experimental developer commands callable without presenting them as
    # public end-user features in `--help`.
    subparsers._choices_actions = [  # type: ignore[attr-defined]
        action
        for action in subparsers._choices_actions  # type: ignore[attr-defined]
        if action.dest not in {"density", "mo"}
    ]

    args = parser.parse_args()

    if getattr(args, "command", None) == "formchk":
        try:
            output_path = convert_chk_to_fchk(args.file, args.output)
        except Exception as e:
            utils.print_error(str(e))
            return 1
        utils.print_success(f"Formatted checkpoint ready: {output_path}")
        return 0

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

        if args.command == "view": # type: ignore
            output_path = args.save or f"{Path(filename).stem}_viewer.html"
            return cmd.cmd_view(
                output_path,
                atomic_numbers,
                coordinates,
                open_browser=bool(args.open and not args.no_open),
                show_labels=not args.no_labels,
                style=args.style,
            )

        if args.command == "interactive": # type: ignore
            run_interactive(lines, fchk_file)
            return 0
    except Exception as e:
        utils.print_error(str(e))
        return 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
