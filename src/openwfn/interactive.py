from pathlib import Path
from typing import Callable

from . import commands as cmd  # type: ignore
from . import utils  # type: ignore
from .fchk import parse_fchk_arrays, parse_fchk_scalars, print_atom_table  # type: ignore
from .geometry import molecular_formula  # type: ignore

OPENWFN_ASCII = [
    "  ___   ____   _____  _   _ __        __ _____  _   _ ",
    " / _ \\ |  _ \\ | ____|| \\ | |\\ \\      / /|  ___|| \\ | |",
    "| | | || |_) ||  _|  |  \\| | \\ \\ /\\ / / | |_   |  \\| |",
    "| |_| ||  __/ | |___ | |\\  |  \\ V  V /  |  _|  | |\\  |",
    " \\___/ |_|    |_____||_| \\_|   \\_/\\_/   |_|    |_| \\_|",
]

PRODUCT_NAME = "openWFN"
PRODUCT_EXPANSION = "Open WaveFunction Network"


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
    "7": "xyz",
    "xyz": "xyz",
    "export": "xyz",
    "8": "view",
    "view": "view",
    "viewer": "view",
    "9": "bonds",
    "bonds": "bonds",
    "10": "graph",
    "graph": "graph",
    "fragments": "graph",
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


def print_landing_page(filename: str, atomic_numbers: list[int], scalars: dict[str, object]) -> None:
    """Display the interactive landing page."""
    print()
    for line in OPENWFN_ASCII:
        print(utils.highlight(line))
    utils.print_panel(
        PRODUCT_EXPANSION,
        [
            "A lightweight terminal toolkit for Gaussian .fchk geometry analysis.",
            "",
            f"File      : {filename}",
            f"Formula   : {molecular_formula(atomic_numbers)}",
            f"Atoms     : {len(atomic_numbers)}",
            f"Charge    : {scalars.get('Charge', 'N/A')}",
            f"Spin Mult : {scalars.get('Multiplicity', 'N/A')}",
        ],
    )
    utils.print_menu_section(
        "Stable Features",
        [
            ("1", "Molecular summary"),
            ("2", "Detailed metadata"),
            ("3", "Atom index table"),
            ("4", "Distance between two atoms"),
            ("5", "Bond angle (i-j-k)"),
            ("6", "Dihedral angle (i-j-k-l)"),
            ("7", "Export XYZ coordinates"),
            ("8", "Open molecule viewer"),
            ("9", "List detected covalent bonds"),
            ("10", "Show fragments / connectivity"),
        ],
    )
    utils.print_menu_section(
        "Session",
        [
            ("0", "Exit"),
        ],
    )
    print(
        f"\n{utils.highlight('Tip:')} choose a feature to open its page. "
        "Every page supports `back` and `exit`. You can also type feature names like "
        "`graph`, `dist`, `summary`, `xyz`, or `view`."
    )
    print()


def print_feature_page(title: str, description: str) -> None:
    """Print a feature page header."""
    utils.print_header(title)
    print(description)
    print(f"\n{utils.highlight('Navigation:')} type `back` to return to the landing page or `exit` to quit.\n")


def prompt_page_navigation(prompt_label: str) -> str:
    """Read page navigation input."""
    while True:
        try:
            choice = input(f"{utils.highlight(prompt_label)} > ").strip().lower()
        except EOFError:
            print("\n")
            return "exit"

        if choice in {"back", "b", "0"}:
            return "back"
        if choice in {"exit", "quit", "x"}:
            return "exit"
        utils.print_error("Type `back` to return or `exit` to quit.")


def run_static_page(title: str, description: str, render: Callable[[], None]) -> str:
    """Render a feature page that does not require extra user input."""
    print_feature_page(title, description)
    render()
    print()
    return prompt_page_navigation(title)


def run_input_page(title: str, description: str, action: Callable[[], None]) -> str:
    """Render a feature page that prompts for additional input."""
    while True:
        print_feature_page(title, description)
        action()
        print()
        nav = prompt_page_navigation(title)
        if nav in {"back", "exit"}:
            return nav


def run_interactive(lines, filename):
    scalars = parse_fchk_scalars(lines)
    atomic_numbers, coordinates = parse_fchk_arrays(lines)
    menu_filename = str(Path(filename).name)

    def show_summary() -> None:
        cmd.cmd_summary(scalars, atomic_numbers, coordinates)

    def show_info() -> None:
        cmd.cmd_info(scalars, atomic_numbers, coordinates)

    def show_table() -> None:
        utils.print_header("Coordinate Table")
        print_atom_table(atomic_numbers, coordinates)

    def run_distance() -> None:
        indices = prompt_indices(("i", "j"))
        if indices is not None:
            cmd.cmd_dist(indices[0], indices[1], coordinates)

    def run_angle() -> None:
        indices = prompt_indices(("i", "j", "k"))
        if indices is not None:
            cmd.cmd_angle(indices[0], indices[1], indices[2], coordinates)

    def run_dihedral() -> None:
        indices = prompt_indices(("i", "j", "k", "l"))
        if indices is not None:
            cmd.cmd_dihedral(indices[0], indices[1], indices[2], indices[3], coordinates)

    def export_xyz() -> None:
        out = prompt_output_filename(filename)
        if out:
            cmd.cmd_xyz(out, atomic_numbers, coordinates)
        else:
            utils.print_warning("Export cancelled.")

    def open_viewer() -> None:
        cmd.cmd_view(None, atomic_numbers, coordinates)

    def show_bonds() -> None:
        cmd.cmd_bonds(atomic_numbers, coordinates)

    def show_graph() -> None:
        cmd.cmd_graph(atomic_numbers, coordinates)

    while True:
        print_landing_page(menu_filename, atomic_numbers, scalars)

        try:
            raw_choice = input(f"{utils.highlight(PRODUCT_NAME)} > ").strip().lower()
        except EOFError:
            print("\nExiting openWFN.")
            break

        action = FEATURE_ALIASES.get(raw_choice, "")

        if action == "summary":
            nav = run_static_page("Molecular Summary", "A one-page overview of the current molecule.", show_summary)
        elif action == "info":
            nav = run_static_page("Detailed Metadata", "Full scalar metadata parsed from the FCHK file.", show_info)
        elif action == "table":
            nav = run_static_page("Atom Index Table", "Atom labels and Cartesian coordinates for reference.", show_table)
        elif action == "dist":
            nav = run_input_page("Distance", "Measure the distance between two atoms.", run_distance)
        elif action == "angle":
            nav = run_input_page("Bond Angle", "Measure an i-j-k bond angle in degrees.", run_angle)
        elif action == "dihedral":
            nav = run_input_page("Dihedral Angle", "Measure an i-j-k-l torsion angle in degrees.", run_dihedral)
        elif action == "xyz":
            nav = run_input_page("Export XYZ", "Write the current coordinates to an XYZ file.", export_xyz)
        elif action == "view":
            nav = run_static_page("Molecule Viewer", "Open the current molecule in a browser-based viewer.", open_viewer)
        elif action == "bonds":
            nav = run_static_page("Detected Bonds", "List covalent bonds using tabulated covalent radii.", show_bonds)
        elif action == "graph":
            nav = run_static_page("Fragments", "Show molecular connectivity and fragment membership.", show_graph)
        elif action == "exit":
            print("\nExiting openWFN.")
            break
        else:
            utils.print_error("Unknown feature. Choose a feature number or type `exit`.")
            continue

        if nav == "exit":
            print("\nExiting openWFN.")
            break
