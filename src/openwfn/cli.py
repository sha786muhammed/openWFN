# src/openwfn/cli.py

import argparse
import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Any

from . import (
    __version__,
    utils,  # type: ignore
)
from . import commands as cmd  # type: ignore
from .analysis.orbitals import frontier_orbitals
from .app import CommandContext, execute
from .batch import run_batch
from .compat import translate_legacy_args
from .exporters.images import write_frontier_diagram
from .exporters.structures import write_structure
from .exporters.tables import ExportRequest, write_result_table
from .fchk import parse_fchk_arrays, parse_fchk_scalars, read_fchk  # type: ignore
from .interactive import run_interactive  # type: ignore
from .parsers.registry import load as load_calculation
from .reporting import build_report_record
from .results import ResultRecord
from .services import (
    density_cube_export,
    density_integration,
    electrostatic_potential_point,
    geometry_angle,
    geometry_dihedral,
    geometry_distance,
    orbital_frontier,
    population_analysis,
)
from .workbench.export import export_workbench_record

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

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="openwfn",
        description=(
            "openWFN — reproducible Gaussian wavefunction analysis, reporting, "
            "and offline molecular visualization."
        )
    )

    parser.add_argument("--version", action="version", version=f"openWFN {__version__}")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--format", choices=["table", "plain", "json", "csv"], default="table")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--plain", action="store_true")
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("file", nargs="?", help="Molecular or quantum-chemistry input file")

    subparsers = parser.add_subparsers(
        dest="command",
        metavar="COMMAND",
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

    # preferred nested geometry interface
    p_geometry = subparsers.add_parser("geometry", help="Distances, angles, dihedrals, and geometry properties")
    geometry_commands = p_geometry.add_subparsers(dest="geometry_command", required=True)
    p_geometry_distance = geometry_commands.add_parser("distance", help="Distance between two atoms")
    p_geometry_distance.add_argument("i", type=int)
    p_geometry_distance.add_argument("j", type=int)
    p_geometry_angle = geometry_commands.add_parser("angle", help="Angle between three atoms")
    p_geometry_angle.add_argument("i", type=int)
    p_geometry_angle.add_argument("j", type=int)
    p_geometry_angle.add_argument("k", type=int)
    p_geometry_dihedral = geometry_commands.add_parser("dihedral", help="Signed four-atom dihedral")
    p_geometry_dihedral.add_argument("i", type=int)
    p_geometry_dihedral.add_argument("j", type=int)
    p_geometry_dihedral.add_argument("k", type=int)
    p_geometry_dihedral.add_argument("l", type=int)

    p_population = subparsers.add_parser("population", help="Mulliken and Löwdin population analysis")
    population_commands = p_population.add_subparsers(dest="population_method", required=True)
    population_commands.add_parser("mulliken", help="Compute Mulliken atomic populations and charges")
    population_commands.add_parser("lowdin", help="Compute symmetric Löwdin populations and charges")

    p_orbitals = subparsers.add_parser("orbitals", help="Molecular orbital analysis")
    orbital_commands = p_orbitals.add_subparsers(dest="orbital_command", required=True)
    p_frontier = orbital_commands.add_parser("frontier", help="Report HOMO, LUMO, and energy gap")
    p_frontier.add_argument("--spin", choices=["alpha", "beta"], default="alpha")

    p_density = subparsers.add_parser("density", help="Electron and spin-density analysis")
    density_commands = p_density.add_subparsers(dest="density_command", required=True)
    p_density_integrate = density_commands.add_parser("integrate", help="Integrate density on a molecular grid")
    p_density_cube = density_commands.add_parser("cube", help="Export density as a Gaussian cube")
    p_density_cube.add_argument("cube_output", type=Path)
    for density_parser in (p_density_integrate, p_density_cube):
        density_parser.add_argument("--kind", choices=["total", "alpha", "beta", "spin"], default="total")
        density_parser.add_argument("--spacing", type=float, default=0.15, help="Grid spacing in bohr")
        density_parser.add_argument("--padding", type=float, default=6.0, help="Padding around molecule in bohr")

    p_esp = subparsers.add_parser("esp", help="Electrostatic-potential analysis")
    esp_commands = p_esp.add_subparsers(dest="esp_command", required=True)
    p_esp_point = esp_commands.add_parser("point", help="Evaluate ESP at one Cartesian point")
    p_esp_point.add_argument("x", type=float)
    p_esp_point.add_argument("y", type=float)
    p_esp_point.add_argument("z", type=float)
    p_esp_point.add_argument(
        "--component",
        choices=["nuclear", "mulliken", "lowdin", "electronic", "total"],
        default="total",
    )
    p_esp_point.add_argument("--spacing", type=float, default=0.15)
    p_esp_point.add_argument("--padding", type=float, default=6.0)

    p_report = subparsers.add_parser("report", help="Create reproducible research reports")
    report_commands = p_report.add_subparsers(dest="report_command", required=True)
    p_report_build = report_commands.add_parser("build", help="Build a self-contained report")
    p_report_build.add_argument("report_output", type=Path)
    p_report_build.add_argument("--report-format", choices=["html", "markdown"], default="html")
    p_report_build.add_argument(
        "--analyses", default="summary,frontier,mulliken,lowdin",
        help="Comma-separated analyses",
    )

    p_workbench = subparsers.add_parser("workbench", help="Export the offline molecular workbench")
    p_workbench.add_argument("workbench_output", nargs="?", type=Path)
    p_workbench.add_argument("--open", action="store_true", dest="open_workbench")

    p_cube = subparsers.add_parser("cube", help="Export volumetric electron-density data")
    p_cube.add_argument("cube_output", type=Path)
    p_cube.add_argument("--kind", choices=["total", "alpha", "beta", "spin"], default="total")
    p_cube.add_argument("--spacing", type=float, default=0.15)
    p_cube.add_argument("--padding", type=float, default=6.0)

    p_convert = subparsers.add_parser("convert", help="Convert to a molecular structure format")
    p_convert.add_argument("--to", choices=["xyz", "pdb", "mol", "sdf"], required=True)
    p_convert.add_argument("--output", dest="convert_output", type=Path, required=True)

    p_export = subparsers.add_parser("export", help="Export a scientific result table")
    p_export.add_argument("analysis", choices=["frontier", "mulliken", "lowdin"])
    p_export.add_argument("export_output", type=Path)

    p_plot = subparsers.add_parser("plot", help="Create a publication-ready scientific figure")
    p_plot.add_argument("analysis", choices=["frontier"])
    p_plot.add_argument("plot_output", type=Path)
    p_plot.add_argument("--dpi", type=int, default=300)

    p_batch = subparsers.add_parser("batch", help="Analyze multiple inputs reproducibly")
    p_batch.add_argument("inputs", nargs="*", type=Path)
    p_batch.add_argument("--operation", choices=["summary"], default="summary")
    p_batch.add_argument("--workers", type=int, default=1)
    p_batch.add_argument("--output-dir", type=Path, required=True)
    p_batch.add_argument("--fail-fast", action="store_true")

    subparsers.add_parser("validate", help="Validate numerical density electron conservation")
    subparsers.add_parser("doctor", help="Inspect parsed data and available analysis capabilities")

    # mo
    p_mo = subparsers.add_parser(
        "mo",
        help=argparse.SUPPRESS,
        description="Experimental developer preview: molecular-orbital export pathway.",
    )
    p_mo.add_argument("index", type=int, help="MO index")
    p_mo.add_argument("--export", required=True, help="Output VTK file path")

    # Keep the obsolete developer-only MO-grid command out of public help.
    subparsers._choices_actions = [  # type: ignore[attr-defined]
        action
        for action in subparsers._choices_actions  # type: ignore[attr-defined]
        if action.dest != "mo"
    ]

    raw_arguments = sys.argv[1:] if argv is None else argv
    args = parser.parse_args(translate_legacy_args(raw_arguments))

    if args.file is None:
        parser.error("an input file is required unless --version is used")

    if args.command == "geometry":
        context = CommandContext(
            input_path=Path(args.file),
            output_path=args.output,
            format="plain" if args.plain else args.format,
            color=not args.no_color and args.format == "table",
            quiet=args.quiet,
            verbose=args.verbose,
            debug=args.debug,
            compact=args.compact,
            overwrite=args.overwrite,
        )
        calculation = load_calculation(Path(args.file))
        operations = {
            "distance": lambda: geometry_distance(calculation.molecule, args.i, args.j),
            "angle": lambda: geometry_angle(calculation.molecule, args.i, args.j, args.k),
            "dihedral": lambda: geometry_dihedral(
                calculation.molecule, args.i, args.j, args.k, args.l
            ),
        }
        return execute(operations[args.geometry_command], context)

    if args.command == "population":
        context = CommandContext(
            input_path=Path(args.file),
            output_path=args.output,
            format="plain" if args.plain else args.format,
            color=not args.no_color and args.format == "table",
            quiet=args.quiet,
            verbose=args.verbose,
            debug=args.debug,
            compact=args.compact,
            overwrite=args.overwrite,
        )
        calculation = load_calculation(Path(args.file))
        return execute(lambda: population_analysis(calculation, args.population_method), context)

    if args.command == "orbitals":
        context = CommandContext(
            input_path=Path(args.file),
            output_path=args.output,
            format="plain" if args.plain else args.format,
            color=not args.no_color and args.format == "table",
            quiet=args.quiet,
            verbose=args.verbose,
            debug=args.debug,
            compact=args.compact,
            overwrite=args.overwrite,
        )
        calculation = load_calculation(Path(args.file))
        return execute(lambda: orbital_frontier(calculation, args.spin), context)

    if args.command == "density":
        context = CommandContext(
            input_path=Path(args.file), output_path=args.output,
            format="plain" if args.plain else args.format,
            color=not args.no_color and args.format == "table", quiet=args.quiet,
            verbose=args.verbose, debug=args.debug, compact=args.compact,
            overwrite=args.overwrite,
        )
        calculation = load_calculation(Path(args.file))
        if args.density_command == "integrate":
            return execute(
                lambda: density_integration(calculation, args.kind, args.spacing, args.padding),
                context,
            )
        return execute(
            lambda: density_cube_export(
                calculation, args.kind, args.spacing, args.padding,
                args.cube_output, args.overwrite,
            ),
            context,
        )

    if args.command == "esp":
        context = CommandContext(
            input_path=Path(args.file), output_path=args.output,
            format="plain" if args.plain else args.format,
            color=not args.no_color and args.format == "table", quiet=args.quiet,
            verbose=args.verbose, debug=args.debug, compact=args.compact,
            overwrite=args.overwrite,
        )
        calculation = load_calculation(Path(args.file))
        return execute(
            lambda: electrostatic_potential_point(
                calculation, (args.x, args.y, args.z), args.component,
                args.spacing, args.padding,
            ),
            context,
        )

    if args.command == "report":
        context = CommandContext(
            input_path=Path(args.file), output_path=args.report_output,
            format="plain" if args.plain else args.format,
            color=not args.no_color and args.format == "table", quiet=args.quiet,
            verbose=args.verbose, debug=args.debug, compact=args.compact,
            overwrite=args.overwrite,
        )
        calculation = load_calculation(Path(args.file))
        analyses = tuple(item.strip() for item in args.analyses.split(",") if item.strip())
        command = "openwfn " + " ".join(raw_arguments)
        return execute(
            lambda: build_report_record(
                calculation, analyses, args.report_output, args.report_format,
                command, args.overwrite,
            ),
            context,
        )

    if args.command == "workbench":
        calculation = load_calculation(Path(args.file))
        output = args.workbench_output or Path(f"{Path(args.file).stem}-workbench.html")
        context = CommandContext(
            input_path=Path(args.file), output_path=output,
            format="plain" if args.plain else args.format,
            color=not args.no_color and args.format == "table", quiet=args.quiet,
            verbose=args.verbose, debug=args.debug, compact=args.compact,
            overwrite=args.overwrite,
        )
        status = execute(
            lambda: export_workbench_record(calculation, output, overwrite=args.overwrite),
            context,
        )
        if status == 0 and args.open_workbench:
            webbrowser.open(output.resolve().as_uri())
        return status

    if args.command in {"cube", "convert", "export", "plot", "batch", "validate", "doctor"}:
        context = CommandContext(
            input_path=Path(args.file), output_path=args.output,
            format="plain" if args.plain else args.format,
            color=not args.no_color and args.format == "table", quiet=args.quiet,
            verbose=args.verbose, debug=args.debug, compact=args.compact,
            overwrite=args.overwrite,
        )
        if args.command == "batch":
            inputs = [Path(args.file), *args.inputs]
            def batch_operation() -> ResultRecord:
                manifest = run_batch(
                    inputs, args.operation, args.workers, args.output_dir, args.fail_fast
                )
                successes = sum(record.status == "success" for record in manifest.records)
                return ResultRecord(
                    kind="batch",
                    data={
                        "operation": manifest.operation,
                        "inputs": len(manifest.records),
                        "successes": successes,
                        "errors": len(manifest.records) - successes,
                        "manifest": str(args.output_dir / "batch-manifest.json"),
                    },
                )
            return execute(batch_operation, context)

        calculation = load_calculation(Path(args.file))
        if args.command == "cube":
            return execute(
                lambda: density_cube_export(
                    calculation, args.kind, args.spacing, args.padding,
                    args.cube_output, args.overwrite,
                ), context,
            )
        if args.command == "convert":
            def convert_operation() -> ResultRecord:
                write_structure(
                    calculation.molecule, args.convert_output, args.to, args.overwrite
                )
                return ResultRecord(
                    kind="structure_export",
                    data={"format": args.to, "output": str(args.convert_output)},
                )
            return execute(convert_operation, context)
        if args.command == "export":
            def export_operation() -> ResultRecord:
                result = (
                    orbital_frontier(calculation)
                    if args.analysis == "frontier"
                    else population_analysis(calculation, args.analysis)
                )
                output_format = args.export_output.suffix.lstrip(".").lower()
                write_result_table(
                    result,
                    ExportRequest(args.export_output, output_format, args.overwrite),
                )
                return ResultRecord(
                    kind="table_export",
                    data={"analysis": args.analysis, "output": str(args.export_output)},
                )
            return execute(export_operation, context)
        if args.command == "plot":
            def plot_operation() -> ResultRecord:
                if calculation.alpha_orbitals is None:
                    raise ValueError("Molecular orbital data are not available.")
                frontier = frontier_orbitals(calculation.alpha_orbitals)
                output_format = args.plot_output.suffix.lstrip(".").lower()
                write_frontier_diagram(
                    frontier,
                    ExportRequest(args.plot_output, output_format, args.overwrite, args.dpi),
                )
                return ResultRecord(
                    kind="figure_export",
                    data={"analysis": "frontier", "output": str(args.plot_output)},
                )
            return execute(plot_operation, context)
        if args.command == "validate":
            return execute(
                lambda: density_integration(calculation, "total", 0.15, 6.0), context
            )
        available = {
            "basis": calculation.basis is not None,
            "orbitals": calculation.alpha_orbitals is not None,
            "density": calculation.total_density is not None,
        }
        return execute(
            lambda: ResultRecord(
                kind="doctor",
                data={"input": str(args.file), "capabilities": available},
            ), context,
        )

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
