from pathlib import Path
from typing import Callable

from . import (
    __version__,  # type: ignore
    utils,  # type: ignore
)
from . import commands as cmd  # type: ignore
from .api import load
from .app import CommandContext
from .errors import DataUnavailableError
from .fchk import print_atom_table  # type: ignore
from .geometry import molecular_formula  # type: ignore
from .palette import prompt_workflow
from .presentation import render
from .reporting import build_report_record
from .results import ResultRecord
from .workbench.export import export_workbench_record

OPENWFN_ASCII = [
    "██████╗ ██████╗ ███████╗███╗   ██╗██╗    ██╗███████╗███╗   ██╗",
    "██╔══██╗██╔══██╗██╔════╝████╗  ██║██║    ██║██╔════╝████╗  ██║",
    "██║  ██║██████╔╝█████╗  ██╔██╗ ██║██║ █╗ ██║█████╗  ██╔██╗ ██║",
    "██║  ██║██╔═══╝ ██╔══╝  ██║╚██╗██║██║███╗██║██╔══╝  ██║╚██╗██║",
    "██████╔╝██║     ███████╗██║ ╚████║╚███╔███╔╝██║     ██║ ╚████║",
    "╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝ ╚══╝╚══╝ ╚═╝     ╚═╝  ╚═══╝",
]

PRODUCT_NAME = "openWFN"
PRODUCT_EXPANSION = "Open WaveFunction Network"
PRODUCT_TAGLINE = "Scientific geometry, orbitals, and density analysis for normalized molecular wavefunctions."
AUTHOR_CREDIT = "Muhammed Shah Shaji"


FEATURE_ALIASES = {
    "1": "summary",
    "summary": "summary",
    "2": "info",
    "info": "info",
    "3": "table",
    "table": "table",
    "atoms": "table",
    "4": "dist",
    "dist": "dist",
    "distance": "dist",
    "5": "angle",
    "angle": "angle",
    "6": "dihedral",
    "dihedral": "dihedral",
    "7": "bonds",
    "bonds": "bonds",
    "8": "graph",
    "graph": "graph",
    "fragments": "graph",
    "9": "xyz",
    "xyz": "xyz",
    "export": "export",
    "10": "view",
    "view": "view",
    "viewer": "view",
    "vibrations": "vibrations",
    "spectra": "vibrations",
    "0": "exit",
    "exit": "exit",
    "quit": "exit",
}


def prompt_int(prompt: str) -> int | None:
    """Prompt until a valid integer is entered or the user leaves it blank."""
    while True:
        try:
            value = input(prompt).strip()
        except EOFError:
            return None

        if not value:
            return None

        try:
            return int(value)
        except ValueError:
            utils.print_error("Please enter a whole-number atom index, or press Enter to cancel.")


def prompt_indices(labels: tuple[str, ...]) -> list[int] | None:
    """Read a fixed number of 1-based atom indices."""
    values: list[int] = []
    for label in labels:
        value = prompt_int(f"Enter atom {label} (1-based index, blank to cancel): ")
        if value is None:
            utils.print_warning("Action cancelled.")
            return None
        values.append(value)
    return values


def prompt_output_filename(source_filename: str) -> str | None:
    """Prompt for an output path, suggesting a sensible default."""
    default_name = f"{Path(source_filename).stem}.xyz"
    try:
        raw_value = input(f"Enter output XYZ filename [{default_name}]: ").strip()
    except EOFError:
        return None

    return raw_value or default_name


def prompt_viewer_filename(source_filename: str) -> str | None:
    """Prompt for a standalone HTML viewer filename."""
    default_name = f"{Path(source_filename).stem}_viewer.html"
    try:
        raw_value = input(f"Enter output HTML viewer filename [{default_name}]: ").strip()
    except EOFError:
        return None

    return raw_value or default_name


def prompt_open_in_browser() -> bool:
    """Ask whether the exported viewer should be opened immediately."""
    while True:
        try:
            raw_value = input("Open exported viewer in browser now? [y/N]: ").strip().lower()
        except EOFError:
            return False

        if raw_value in {"", "n", "no"}:
            return False
        if raw_value in {"y", "yes"}:
            return True
        utils.print_error("Enter `y` to open the browser or `n` to keep the HTML file only.")


def print_landing_page(filename: str, atomic_numbers: list[int], scalars: dict[str, object]) -> None:
    """Display the interactive landing page."""
    formula = molecular_formula(atomic_numbers)
    multiplicity = scalars.get("Multiplicity", "N/A")
    spin_label = "singlet" if multiplicity == 1 else f"multiplicity {multiplicity}"
    print(f"\n{PRODUCT_NAME} {__version__}  /  {filename}\n")
    print(
        f"{formula}  ·  {len(atomic_numbers)} atoms  ·  "
        f"charge {scalars.get('Charge', 'N/A')}  ·  {spin_label}"
    )
    print("● Ready\n")
    print("Select a workflow\n")
    for label in (
        "Inspect molecular structure",
        "Analyze geometry",
        "Explore bonds and fragments",
        "Analyze molecular orbitals",
        "Analyze vibrations and spectra",
        "Calculate density and ESP",
        "Open 3D workbench",
        "Export or convert data",
        "Create research report",
        "Validate calculation",
    ):
        print(f"  {label}")
    print("\n↑↓ navigate   enter select   / search   q quit\n")


def print_feature_page(title: str, description: str) -> None:
    """Print a feature page header."""
    utils.print_header(title)
    print(description)
    print(f"\n{utils.highlight('Navigation:')} enter `back` to return to the landing page or `exit` to quit.\n")


def prompt_page_navigation(prompt_label: str) -> str:
    """Read page navigation input."""
    prompt_name = prompt_label.lower().replace(" ", "-")
    while True:
        try:
            choice = input(f"{utils.highlight(f'{PRODUCT_NAME}/{prompt_name}')} > ").strip().lower()
        except EOFError:
            print("\n")
            return "exit"

        if choice in {"back", "b", "0"}:
            return "back"
        if choice in {"exit", "quit", "x"}:
            return "exit"
        utils.print_error("Enter `back` to return or `exit` to quit.")


def run_guided_action(action: Callable[[], None], title: str) -> None:
    """Keep expected input/data failures inside the standard result boundary."""
    try:
        action()
    except (DataUnavailableError, ValueError, IndexError, FileExistsError) as exc:
        record = ResultRecord.failure(kind="guided_workflow", analysis_name=title,
                                      analysis_version="1", exception=exc, elapsed_seconds=0.)
        print(render(record, CommandContext(format="plain")), end="")


def run_static_page(title: str, description: str, render: Callable[[], None]) -> str:
    """Render a feature page that does not require extra user input."""
    print_feature_page(title, description)
    run_guided_action(render, title)
    print()
    return prompt_page_navigation(title)


def run_input_page(title: str, description: str, action: Callable[[], None]) -> str:
    """Render a feature page that prompts for additional input."""
    while True:
        print_feature_page(title, description)
        run_guided_action(action, title)
        print()
        nav = prompt_page_navigation(title)
        if nav in {"back", "exit"}:
            return nav


def run_interactive(lines, filename):
    client = load(Path(filename))
    calculation = client.data.calculation
    if calculation is None:
        raise DataUnavailableError("Guided wavefunction workflows require an isolated molecular calculation.")
    molecule = calculation.molecule
    atomic_numbers = [atom.atomic_number for atom in molecule.atoms]
    coordinates = [atom.coordinates for atom in molecule.atoms]
    scalars = {"Charge": molecule.charge, "Multiplicity": molecule.multiplicity,
               "Number of atoms": len(molecule.atoms)}
    menu_filename = str(Path(filename).name)

    def show_result(result) -> None:
        print(render(result, CommandContext(input_path=Path(filename), format="plain")), end="")

    def show_summary() -> None:
        show_result(client.analyze("summary"))

    def show_info() -> None:
        cmd.cmd_info(scalars, atomic_numbers, coordinates)

    def show_table() -> None:
        utils.print_header("Coordinate Table")
        print_atom_table(atomic_numbers, coordinates)

    def run_distance() -> None:
        indices = prompt_indices(("i", "j"))
        if indices is not None:
            show_result(client.geometry_distance(*indices))

    def run_angle() -> None:
        indices = prompt_indices(("i", "j", "k"))
        if indices is not None:
            show_result(client.geometry_angle(*indices))

    def run_dihedral() -> None:
        indices = prompt_indices(("i", "j", "k", "l"))
        if indices is not None:
            show_result(client.geometry_dihedral(*indices))

    def export_xyz() -> None:
        out = prompt_output_filename(filename)
        if out:
            cmd.cmd_xyz(out, atomic_numbers, coordinates)
        else:
            utils.print_warning("Export cancelled.")

    def open_viewer() -> None:
        default_name = f"{Path(filename).stem}-workbench.html"
        try:
            out = input(f"Enter output HTML workbench filename [{default_name}]: ").strip()
        except EOFError:
            out = ""
        out = out or default_name
        if out:
            open_browser = prompt_open_in_browser()
            show_result(export_workbench_record(calculation, Path(out)))
            if open_browser:
                import webbrowser

                webbrowser.open(Path(out).resolve().as_uri())
        else:
            utils.print_warning("Viewer export cancelled.")

    def ask(prompt: str, default: str) -> str:
        try:
            return input(prompt).strip() or default
        except EOFError:
            return default

    def show_orbitals() -> None:
        operation = ask("Orbital analysis [frontier/composition/cube/dos/pdos; default frontier]: ", "frontier").casefold()
        spin = ask("Spin channel [alpha/beta/all; default alpha]: ", "alpha").casefold()
        if operation == "frontier":
            show_result(client.orbitals(spin))
        elif operation in {"composition", "cube"}:
            mo = ask("MO [homo/lumo/one-based number; default homo]: ", "homo")
            if operation == "composition":
                method = ask("Population convention [lowdin/mulliken; default lowdin]: ", "lowdin")
                show_result(client.orbital_composition(mo=mo, spin=spin, method=method))
            else:
                output = ask("Output cube path [orbital.cube]: ", "orbital.cube")
                show_result(client.orbital_cube(output, mo=mo, spin=spin))
        elif operation in {"dos", "pdos"}:
            show_result(client.dos(spin=spin) if operation == "dos" else client.pdos(spin=spin))
        else:
            utils.print_error("Unknown orbital analysis.")

    def show_vibrations() -> None:
        operation = ask(
            "Vibrational workflow [modes/ir/raman/mode; default modes]: ", "modes"
        ).casefold()
        if operation in {"modes", "vibrations"}:
            show_result(client.analyze("vibrations"))
        elif operation == "ir":
            show_result(client.analyze("ir-spectrum"))
        elif operation == "raman":
            show_result(client.analyze("raman-spectrum"))
        elif operation == "mode":
            mode = int(ask("One-based mode number [1]: ", "1"))
            show_result(client.analyze("normal-mode", mode=mode))
        else:
            utils.print_error("Unknown vibrational workflow.")

    def show_density() -> None:
        operation = ask("Density workflow [integrate/esp; default integrate]: ", "integrate").casefold()
        if operation == "integrate":
            kind = ask("Density component [total/alpha/beta/spin; default total]: ", "total").casefold()
            show_result(client.density(kind))
        elif operation == "esp":
            point = tuple(float(value) for value in ask("ESP coordinates x y z in angstrom [5 0 0]: ", "5 0 0").split())
            component = ask("ESP component [total/electronic/nuclear/mulliken/lowdin; default total]: ", "total")
            show_result(client.esp(point, component=component))
        else:
            utils.print_error("Unknown density workflow.")

    def create_report() -> None:
        output = Path(f"{Path(filename).stem}-report.html")
        show_result(
            build_report_record(
                calculation,
                ("summary", "frontier", "mulliken", "lowdin"),
                output,
                "html",
                f"openwfn {filename} report build {output}",
                False,
            )
        )

    def show_bonds() -> None:
        method = ask("Bond analysis [geometry/mayer/fragments; default geometry]: ", "geometry").casefold()
        if method == "mayer":
            show_result(client.mayer())
        elif method == "fragments":
            show_graph()
        elif method == "geometry":
            cmd.cmd_bonds(atomic_numbers, coordinates)
        else:
            utils.print_error("Unknown bond analysis.")

    def show_graph() -> None:
        cmd.cmd_graph(atomic_numbers, coordinates)

    while True:
        print_landing_page(menu_filename, atomic_numbers, scalars)

        raw_choice = prompt_workflow()
        action = FEATURE_ALIASES.get(raw_choice, raw_choice)

        if action == "summary":
            nav = run_static_page("Molecular Summary", "A one-page overview of the current molecule.", show_summary)
        elif action == "geometry":
            try:
                geometry_choice = input("Geometry command [distance/angle/dihedral/back]: ").strip().casefold()
            except EOFError:
                geometry_choice = "back"
            if geometry_choice in {"distance", "dist"}:
                nav = run_input_page("Distance", "Measure the distance between two atoms.", run_distance)
            elif geometry_choice == "angle":
                nav = run_input_page("Bond Angle", "Measure an i-j-k bond angle in degrees.", run_angle)
            elif geometry_choice == "dihedral":
                nav = run_input_page("Dihedral Angle", "Measure an i-j-k-l torsion angle in degrees.", run_dihedral)
            else:
                continue
        elif action == "export":
            nav = run_input_page("Export XYZ", "Write the current coordinates to an XYZ file.", export_xyz)
        elif action == "workbench":
            nav = run_input_page(
                "3D Workbench",
                "Export the current molecule to a standalone local HTML workbench.",
                open_viewer,
            )
        elif action == "bonds":
            nav = run_static_page("Detected Bonds", "List covalent bonds using tabulated covalent radii.", show_bonds)
        elif action == "orbitals":
            nav = run_static_page("Frontier Orbitals", "Report HOMO, LUMO, and energy gap.", show_orbitals)
        elif action == "vibrations":
            nav = run_static_page(
                "Vibrational Spectroscopy",
                "Inspect source vibrational modes, IR/Raman spectra, or one normal mode.",
                show_vibrations,
            )
        elif action in {"density", "validate"}:
            nav = run_static_page(
                "Density Validation",
                "Integrate total electron density and report conservation error.",
                show_density,
            )
        elif action == "report":
            nav = run_static_page(
                "Research Report", "Create a reproducible self-contained HTML report.", create_report
            )
        elif action in {"exit", "q"}:
            print("\nExiting openWFN.")
            break
        else:
            utils.print_error("Unknown workflow. Enter a displayed command name or `q` to quit.")
            continue

        if nav == "exit":
            print("\nExiting openWFN.")
            break