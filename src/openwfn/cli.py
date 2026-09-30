# src/openwfn/cli.py

import argparse
import json
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
from .analysis.orbitals import frontier_orbitals
from .analysis.registry import run_analysis
from .app import CommandContext, execute
from .batch import discover_inputs, run_batch
from .compat import complete_implicit_command, translate_legacy_args
from .errors import DataUnavailableError
from .export import export_molecule_viewer
from .exporters.structures import write_structure
from .exporters.tables import ExportRequest, write_result_table
from .fchk import parse_fchk_arrays, parse_fchk_scalars, read_fchk  # type: ignore
from .geometry import detect_bonds, molecular_formula
from .graph import build_graph
from .ingest import load_input
from .inspection import build_capabilities_result, capability_payload
from .interactive import run_interactive  # type: ignore
from .model import CalculationData
from .reporting import build_report_record
from .results import ResultRecord
from .services import (
    density_cube_export,
    density_integration,
    electrostatic_potential_point,
    geometry_angle,
    geometry_dihedral,
    geometry_distance,
)
from .workbench.export import export_workbench_record

# -------------------------------------------------
# Utilities
# -------------------------------------------------

def convert_chk_to_fchk(file: str, output: str | None = None, *, quiet: bool = False) -> str:
    """Convert a Gaussian .chk file into a formatted checkpoint file."""
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


def _context(args: argparse.Namespace) -> CommandContext:
    return CommandContext(
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


def _require_calculation(path: Path, *, format_hint: str | None = None) -> CalculationData:
    parsed = load_input(path, format_hint=format_hint)
    if parsed.calculation is None:
        raise DataUnavailableError(
            f"{path} does not contain a molecular calculation. "
            "Use `doctor` to inspect the input's available capabilities."
        )
    return parsed.calculation


def _doctor_result(path: Path, *, format_hint: str | None = None) -> ResultRecord:
    parsed = load_input(path, format_hint=format_hint)
    calculation = parsed.calculation
    if calculation is not None:
        input_kind = "molecular-calculation"
        capabilities = {
            "basis": calculation.basis is not None,
            "density": calculation.total_density is not None,
            "metadata": True,
            "orbitals": calculation.alpha_orbitals is not None,
            "volumetric_grid": False,
        }
    elif parsed.grids:
        input_kind = "volumetric-grid"
        capabilities = {
            "basis": False,
            "density": True,
            "metadata": False,
            "orbitals": False,
            "volumetric_grid": True,
        }
    elif parsed.structure is not None:
        input_kind = "periodic-structure" if parsed.periodic is not None else "structure-only"
        capabilities = {
            "basis": False, "density": False, "metadata": True,
            "orbitals": False, "volumetric_grid": False,
        }
    elif parsed.integrals is not None:
        input_kind = "integral-data"
        capabilities = {
            "basis": False, "density": False, "metadata": True,
            "orbitals": False, "volumetric_grid": False,
        }
    else:
        input_kind = "calculation-metadata"
        capabilities = {
            "basis": False,
            "density": False,
            "metadata": True,
            "orbitals": False,
            "volumetric_grid": False,
        }
    return ResultRecord(
        kind="doctor",
        data={
            "input": str(path),
            "input_kind": input_kind,
            "capabilities": capabilities,
            "normalized": capability_payload(parsed, input_path=path),
        },
    )


def _read_format_map(path: Path | None) -> dict[Path, str]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in payload.items()
    ):
        raise ValueError("Format map must be a JSON object from file paths to format IDs.")
    return {(path.parent / key).resolve(): value for key, value in payload.items()}


def _legacy_result(args: argparse.Namespace) -> ResultRecord:
    """Adapt older command names to the structured output contract."""

    command = args.command
    if command == "formchk":
        output = convert_chk_to_fchk(args.file, args.output, quiet=True)
        return ResultRecord(kind="checkpoint_export", data={"output": output})
    if command == "mo":
        raise DataUnavailableError("Molecular orbital grid evaluation is not implemented yet.")
    if command == "interactive":
        raise DataUnavailableError("Interactive mode cannot produce one JSON result; use a specific command.")

    source = Path(args.file)
    normalized = load_input(source, format_hint=args.input_format)
    calculation = normalized.calculation
    if command == "info":
        if source.suffix.lower() in {".fchk", ".fch"}:
            return ResultRecord(kind="fchk_metadata", data=parse_fchk_scalars(read_fchk(str(source))))
        return ResultRecord(
            kind="input_metadata",
            data={
                "source_format": normalized.provenance.source_format if normalized.provenance else None,
                "source_program": normalized.metadata.source_program,
                "energy_hartree": normalized.metadata.energy_hartree,
            },
        )
    if calculation is None:
        raise DataUnavailableError(f"{source} does not contain a molecular calculation.")
    molecule = calculation.molecule
    coordinates = [atom.coordinates for atom in molecule.atoms]
    atomic_numbers = [atom.atomic_number for atom in molecule.atoms]
    if command == "dist":
        return geometry_distance(molecule, args.i, args.j)
    if command == "angle":
        return geometry_angle(molecule, args.i, args.j, args.k)
    if command == "dihedral":
        return geometry_dihedral(molecule, args.i, args.j, args.k, args.l)
    if command in {"bonds", "graph"}:
        bonds = detect_bonds(atomic_numbers, coordinates)
        if command == "bonds":
            return ResultRecord(
                kind="bonds",
                data={"count": len(bonds), "bonds": [
                    {"atom_i": i, "atom_j": j, "distance_angstrom": distance}
                    for i, j, distance in bonds
                ]},
                units={"distance_angstrom": "angstrom"},
            )
        fragments = build_graph(len(atomic_numbers), bonds).connected_components()
        return ResultRecord(
            kind="graph",
            data={"fragments": [
                {"atoms": group, "formula": molecular_formula([atomic_numbers[i - 1] for i in group])}
                for group in fragments
            ]},
        )
    if command == "xyz":
        output = Path(args.output)
        warnings = write_structure(molecule, output, "xyz", args.overwrite)
        return ResultRecord(
            kind="structure_export", data={"format": "xyz", "output": str(output)},
            warnings=warnings,
        )
    if command == "view":
        output = Path(args.save or f"{source.stem}_viewer.html")
        export_molecule_viewer(
            output, atomic_numbers, coordinates,
            show_labels=not args.no_labels, style=args.style,
        )
        opened = webbrowser.open(output.resolve().as_uri()) if args.open and not args.no_open else False
        warnings = ("Viewer file was created, but the browser did not open.",) if args.open and not args.no_open and not opened else ()
        return ResultRecord(kind="viewer_export", data={"output": str(output), "browser_opened": opened}, warnings=warnings)
    raise ValueError(f"Unsupported legacy command: {command}")


def _run_examples_command(arguments: list[str]) -> int:
    examples_parser = argparse.ArgumentParser(prog="openwfn examples")
    commands = examples_parser.add_subparsers(dest="examples_command", required=True)
    install = commands.add_parser("install", help="Copy packaged examples to a directory")
    install.add_argument("destination", type=Path)
    install.add_argument("--overwrite", action="store_true")
    args = examples_parser.parse_args(arguments)

    from .examples import install_examples

    try:
        written = install_examples(args.destination, overwrite=args.overwrite)
    except FileExistsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    for path in written:
        print(path)
    return 0


# -------------------------------------------------
# Main CLI
# -------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    raw_arguments = sys.argv[1:] if argv is None else argv
    if raw_arguments and raw_arguments[0] == "examples":
        return _run_examples_command(raw_arguments[1:])

    parser = argparse.ArgumentParser(
        prog="openwfn",
        description=(
            "openWFN — reproducible wavefunction and scientific post-processing "
            "across supported quantum-chemistry formats."
        ),
    )

    parser.add_argument("--version", action="version", version=f"openWFN {__version__}")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--format", choices=["table", "plain", "json", "csv"], default="table")
    parser.add_argument("--input-format", metavar="FORMAT_ID", help="Explicit input parser format ID")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--plain", action="store_true")
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("file", nargs="?", help="Molecular or quantum-chemistry input file")

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    subparsers.add_parser("examples", help="Install redistributable example inputs")
    subparsers.add_parser("summary", help="Show professional molecular summary")
    subparsers.add_parser("info", help="Show detailed FCHK metadata")

    p_dist = subparsers.add_parser("dist", help="Distance between two atoms")
    p_dist.add_argument("i", type=int)
    p_dist.add_argument("j", type=int)

    p_angle = subparsers.add_parser("angle", help="Bond angle i-j-k")
    p_angle.add_argument("i", type=int)
    p_angle.add_argument("j", type=int)
    p_angle.add_argument("k", type=int)

    p_dih = subparsers.add_parser("dihedral", help="Dihedral i-j-k-l")
    p_dih.add_argument("i", type=int)
    p_dih.add_argument("j", type=int)
    p_dih.add_argument("k", type=int)
    p_dih.add_argument("l", type=int)

    subparsers.add_parser("bonds", help="Detect covalent bonds")

    p_xyz = subparsers.add_parser("xyz", help="Export XYZ file")
    p_xyz.add_argument("output", help="Output XYZ filename")

    p_formchk = subparsers.add_parser(
        "formchk",
        help="Convert a Gaussian checkpoint (.chk) file into a formatted checkpoint (.fchk)",
    )
    p_formchk.add_argument(
        "output",
        nargs="?",
        help="Optional output .fchk path (defaults to the input name with .fchk)",
    )

    p_view = subparsers.add_parser(
        "view", help="Export a standalone local HTML molecule viewer with atom labels"
    )
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

    subparsers.add_parser("interactive", help="Launch interactive menu mode")
    subparsers.add_parser("graph", help="Show molecular graph components")

    p_geometry = subparsers.add_parser(
        "geometry", help="Distances, angles, dihedrals, and geometry properties"
    )
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
    p_frontier.add_argument("--spin", choices=["alpha", "beta", "all"], default="alpha")

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
        "--analyses",
        default="summary,frontier,mulliken,lowdin",
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
    p_batch.add_argument(
        "--analyses",
        help="Comma-separated registered analyses (for example: summary,frontier)",
    )
    p_batch.add_argument(
        "--spin",
        choices=["alpha", "beta", "all"],
        default="alpha",
        help="Spin channel used when `frontier` is requested",
    )
    p_batch.add_argument("--workers", type=int, default=1)
    p_batch.add_argument("--output-dir", type=Path)
    p_batch.add_argument("--fail-fast", action="store_true")
    p_batch.add_argument("--resume", action="store_true", help="Reuse matching completed inputs")
    p_batch.add_argument("--recursive", action="store_true", help="Discover inputs recursively")
    p_batch.add_argument("--format-map", type=Path, help="JSON map of input paths to format IDs")
    p_batch.add_argument("--dry-run", action="store_true", help="List inputs without analysis")

    p_validate = subparsers.add_parser(
        "validate", help="Validate numerical density electron conservation"
    )
    p_validate.add_argument("--spacing", type=float, default=0.15, help="Grid spacing in bohr")
    p_validate.add_argument("--padding", type=float, default=6.0, help="Padding around molecule in bohr")

    subparsers.add_parser("capabilities", help="Report normalized data and analysis capabilities")
    subparsers.add_parser("doctor", help="Inspect parsed data and available analysis capabilities")

    p_mo = subparsers.add_parser(
        "mo",
        help=argparse.SUPPRESS,
        description="Experimental developer preview: molecular-orbital export pathway.",
    )
    p_mo.add_argument("index", type=int, help="MO index")
    p_mo.add_argument("--export", required=True, help="Output VTK file path")

    subparsers._choices_actions = [  # type: ignore[attr-defined]
        action
        for action in subparsers._choices_actions  # type: ignore[attr-defined]
        if action.dest != "mo"
    ]

    translated_arguments = translate_legacy_args(raw_arguments)
    translated_arguments = complete_implicit_command(
        translated_arguments,
        stdin_is_tty=sys.stdin.isatty(),
    )
    args = parser.parse_args(translated_arguments)

    if args.command == "examples":
        parser.error("use `openwfn examples install DESTINATION` without an input file")

    if args.file is None:
        parser.error("an input file is required unless --version is used")

    if args.command in {
        "formchk", "info", "dist", "angle", "dihedral", "bonds", "graph", "mo", "xyz", "view"
    } or (args.command == "interactive" and args.format == "json"):
        context = _context(args)
        if args.command in {"formchk", "xyz"}:
            context.output_path = None
        return execute(lambda: _legacy_result(args), context)

    def require_calculation() -> CalculationData:
        return _require_calculation(Path(args.file), format_hint=args.input_format)

    if args.command == "summary":
        def summary_operation() -> ResultRecord:
            data = load_input(Path(args.file), format_hint=args.input_format)
            return run_analysis(data, "summary")

        return execute(summary_operation, _context(args))

    if args.command == "geometry":
        context = _context(args)

        def geometry_operation() -> ResultRecord:
            calculation = require_calculation()
            operations = {
                "distance": lambda: geometry_distance(calculation.molecule, args.i, args.j),
                "angle": lambda: geometry_angle(calculation.molecule, args.i, args.j, args.k),
                "dihedral": lambda: geometry_dihedral(
                    calculation.molecule, args.i, args.j, args.k, args.l
                ),
            }
            return operations[args.geometry_command]()

        return execute(geometry_operation, context)

    if args.command == "population":
        return execute(
            lambda: run_analysis(
                require_calculation(), args.population_method
            ),
            _context(args),
        )

    if args.command == "orbitals":
        analysis = {
            "alpha": "frontier",
            "beta": "beta-frontier",
            "all": "frontier-all",
        }[args.spin]
        return execute(
            lambda: run_analysis(require_calculation(), analysis),
            _context(args),
        )

    if args.command == "density":
        context = _context(args)

        def density_operation() -> ResultRecord:
            calculation = require_calculation()
            if args.density_command == "integrate":
                return density_integration(
                    calculation, args.kind, args.spacing, args.padding
                )
            return density_cube_export(
                calculation,
                args.kind,
                args.spacing,
                args.padding,
                args.cube_output,
                args.overwrite,
            )

        return execute(density_operation, context)

    if args.command == "esp":
        return execute(
            lambda: electrostatic_potential_point(
                require_calculation(),
                (args.x, args.y, args.z),
                args.component,
                args.spacing,
                args.padding,
            ),
            _context(args),
        )

    if args.command == "report":
        analyses = tuple(item.strip() for item in args.analyses.split(",") if item.strip())
        command = "openwfn " + " ".join(raw_arguments)
        return execute(
            lambda: build_report_record(
                require_calculation(),
                analyses,
                args.report_output,
                args.report_format,
                command,
                args.overwrite,
            ),
            _context(args),
        )

    if args.command == "workbench":
        output = args.workbench_output or Path(f"{Path(args.file).stem}-workbench.html")
        status = execute(
            lambda: export_workbench_record(
                require_calculation(), output, overwrite=args.overwrite
            ),
            _context(args),
        )
        if status == 0 and args.open_workbench:
            webbrowser.open(output.resolve().as_uri())
        return status

    if args.command == "capabilities":
        return execute(
            lambda: build_capabilities_result(Path(args.file), format_hint=args.input_format),
            _context(args),
        )

    if args.command == "doctor":
        return execute(
            lambda: _doctor_result(Path(args.file), format_hint=args.input_format),
            _context(args),
        )

    if args.command in {"cube", "convert", "export", "plot", "batch", "validate"}:
        context = _context(args)
        if args.command == "batch":
            inputs = [Path(args.file), *args.inputs]
            try:
                format_hints = _read_format_map(args.format_map)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                context.error_stream.write(f"Error: Invalid format map: {exc}\n")
                return 1
            analyses = (
                tuple(item.strip() for item in args.analyses.split(",") if item.strip())
                if args.analyses
                else (args.operation,)
            )
            spin_analysis = {
                "alpha": "frontier",
                "beta": "beta-frontier",
                "all": "frontier-all",
            }[args.spin]
            analyses = tuple(
                spin_analysis if analysis == "frontier" else analysis
                for analysis in analyses
            )
            if args.dry_run:
                discovery = discover_inputs(
                    inputs,
                    recursive=args.recursive,
                    output_dir=args.output_dir,
                    format_hint=args.input_format,
                    format_hints=format_hints,
                )
                return execute(
                    lambda: ResultRecord(
                        kind="batch_dry_run",
                        data={
                            "analyses": list(analyses),
                            "discovered": len(discovery.inputs),
                            "inputs": [str(path) for path in discovery.inputs],
                            "unsupported": len(discovery.unsupported),
                            "unsupported_inputs": [
                                str(path) for path in discovery.unsupported
                            ],
                        },
                    ),
                    context,
                )
            if args.output_dir is None:
                p_batch.error("--output-dir is required unless --dry-run is used")

            def batch_operation() -> ResultRecord:
                def report_progress(completed: int, total: int, record) -> None:
                    context.error_stream.write(
                        f"Batch {completed}/{total}: {record.status} {record.input_path}\n"
                    )

                manifest = run_batch(
                    inputs,
                    args.operation,
                    args.workers,
                    args.output_dir,
                    args.fail_fast,
                    analyses=analyses,
                    resume=args.resume,
                    recursive=args.recursive,
                    format_hint=args.input_format,
                    format_hints=format_hints,
                    progress=None if context.quiet else report_progress,
                )
                successes = sum(record.status == "success" for record in manifest.records)
                partial = sum(record.status == "partial" for record in manifest.records)
                errors = sum(record.status == "error" for record in manifest.records)
                skipped = sum(record.skipped for record in manifest.records)
                return ResultRecord(
                    kind="batch",
                    data={
                        "operation": manifest.operation,
                        "analyses": list(manifest.analyses),
                        "inputs": len(manifest.records),
                        "successes": successes,
                        "partial": partial,
                        "errors": errors,
                        "skipped": skipped,
                        "configuration_fingerprint": manifest.configuration_fingerprint,
                        "unsupported": len(manifest.unsupported_inputs),
                        "manifest": str(args.output_dir / "batch-manifest.json"),
                        "csv_index": str(args.output_dir / "batch-summary.csv"),
                    },
                )

            return execute(batch_operation, context)

        if args.command == "cube":
            return execute(
                lambda: density_cube_export(
                    require_calculation(),
                    args.kind,
                    args.spacing,
                    args.padding,
                    args.cube_output,
                    args.overwrite,
                ),
                context,
            )

        if args.command == "convert":
            def convert_operation() -> ResultRecord:
                calculation = require_calculation()
                warnings = write_structure(
                    calculation.molecule, args.convert_output, args.to, args.overwrite
                )
                return ResultRecord(
                    kind="structure_export",
                    data={"format": args.to, "output": str(args.convert_output)},
                    warnings=warnings,
                )

            return execute(convert_operation, context)

        if args.command == "export":
            def export_operation() -> ResultRecord:
                calculation = require_calculation()
                result = run_analysis(calculation, args.analysis)
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
                from .exporters.images import write_frontier_diagram

                calculation = require_calculation()
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
                lambda: density_integration(
                    require_calculation(),
                    "total",
                    args.spacing,
                    args.padding,
                ),
                context,
            )

    if getattr(args, "command", None) is None:
        if sys.stdin.isatty():
            args.command = "interactive"  # type: ignore
        else:
            return execute(
                lambda: run_analysis(
                    load_input(Path(args.file), format_hint=args.input_format), "summary"
                ),
                _context(args),
            )

    if args.command == "interactive":
        try:
            fchk_file, _scalars, _atomic_numbers, _coordinates = load_data(args.file)
            lines = read_fchk(fchk_file)
            run_interactive(lines, fchk_file)
            return 0
        except Exception as exc:
            context = _context(args)
            return execute(lambda error=exc: (_ for _ in ()).throw(error), context)

    return 1


if __name__ == "__main__":
    sys.exit(main())
