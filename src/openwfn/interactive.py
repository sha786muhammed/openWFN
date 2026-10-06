from math import isfinite, prod
from pathlib import Path
from typing import Callable

from . import (
    __version__,  # type: ignore
    utils,  # type: ignore
)
from . import commands as cmd  # type: ignore
from .analysis.grids import molecular_grid_layout
from .app import CommandContext
from .errors import DataUnavailableError
from .fchk import print_atom_table  # type: ignore
from .geometry import molecular_formula  # type: ignore
from .guided import GuidedSession, available_workflows, build_guided_session
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


def prompt_choice(prompt: str, choices: tuple[str, ...], default: str) -> str:
    """Accept only the displayed enum values; never forward terminal escapes."""
    while True:
        value = input(prompt).strip().casefold() or default
        if value in choices:
            return value
        if value in {"back", "home", "quit", "exit"}:
            raise EOFError
        print("Choose " + ", ".join(choices) + "; or enter back to cancel.")


def prompt_positive_float(prompt: str, default: float) -> float:
    while True:
        value = input(prompt).strip()
        if value.casefold() in {"back", "home", "quit", "exit"}:
            raise EOFError
        try:
            number = float(value) if value else default
            if isfinite(number) and number > 0:
                return number
        except ValueError:
            pass
        print("Enter a positive finite number, or back to cancel.")


def confirm_output_path(session: GuidedSession, label: str, suffix: str) -> Path | None:
    """Confirm a new destination; input and existing files remain protected."""
    default = session.directory / "results" / f"{session.source.stem}-{label}{suffix}"
    while True:
        try:
            value = input(f"Output path [{default}] (back to cancel): ").strip()
            if value.casefold() in {"back", "home", "quit", "exit"}:
                return None
            path = Path(value).expanduser() if value else default
            if not path.suffix:
                path = path.with_suffix(suffix)
            if path.suffix.lower() != suffix:
                print(f"This export requires {suffix}; choose another path.")
                continue
            path = path.resolve()
            if path == session.source or path.exists():
                print("Input and existing files are protected; choose a new output path.")
                continue
            print(f"Save to: {path}")
            if input("Confirm save? [y/N]: ").strip().casefold() not in {"y", "yes"}:
                return None
            path.parent.mkdir(parents=True, exist_ok=True)
            return path
        except (EOFError, KeyboardInterrupt):
            return None
        except OSError as exc:
            print(f"Cannot use that destination: {exc}")


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
        except (EOFError, KeyboardInterrupt):
            print("\n")
            return "exit"

        if choice in {"back", "b", "0", "home"}:
            return "back"
        if choice in {"exit", "quit", "x"}:
            return "exit"
        utils.print_error("Enter `back` to return or `exit` to quit.")


def run_guided_action(action: Callable[[], None], title: str) -> None:
    """Keep expected input/data failures inside the standard result boundary."""
    try:
        action()
    except (EOFError, KeyboardInterrupt):
        print("\nAction cancelled; no default operation was started.")
    except (DataUnavailableError, ValueError, IndexError, OSError) as exc:
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


def run_interactive(lines, filename, *, format_hint=None):
    session = build_guided_session(Path(filename), format_hint=format_hint)
    client = session.calculation
    calculation = client.data.calculation
    structure = client.data.structure
    atoms = structure.coordinates if structure is not None else ()
    atomic_numbers = list(structure.atomic_numbers) if structure is not None else []
    coordinates = list(atoms)
    menu_filename = str(Path(filename).name)

    def show_result(result) -> None:
        print(render(result, CommandContext(input_path=Path(filename), format="plain")), end="")

    def show_summary() -> None:
        show_result(client.analyze("summary"))

    def show_info() -> None:
        cmd.cmd_info({"Charge": structure.charge, "Multiplicity": structure.multiplicity}, atomic_numbers, coordinates)

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
        out = confirm_output_path(session, "structure", ".xyz")
        if out:
            cmd.cmd_xyz(out, atomic_numbers, coordinates)
        else:
            utils.print_warning("Export cancelled.")

    def open_viewer() -> None:
        out = confirm_output_path(session, "workbench", ".html")
        if out:
            open_browser = prompt_open_in_browser()
            show_result(export_workbench_record(calculation, Path(out)))
            if open_browser:
                import webbrowser

                if not webbrowser.open(Path(out).resolve().as_uri()):
                    print(f"Browser did not open. The saved file is available at {out}.")
        else:
            utils.print_warning("Viewer export cancelled.")

    def ask(prompt: str, default: str) -> str:
        return input(prompt).strip() or default

    def show_orbitals() -> None:
        operations = ["frontier"]
        operations.extend(name for name, analysis in (("composition", "orbital-composition"),
                          ("dos", "dos"), ("pdos", "pdos")) if session.eligible(analysis))
        if client.data.basis is not None and client.data.alpha_orbitals is not None:
            operations.append("cube")
        operation = prompt_choice(f"Orbital analysis [{'/'.join(operations)}; default frontier]: ", tuple(operations), "frontier")
        spins = ("alpha", "beta") if client.data.beta_orbitals is not None else ("alpha",)
        if operation in {"frontier", "dos", "pdos"}:
            spins = (*spins, "all")
        spin = prompt_choice(f"Spin channel [{'/'.join(spins)}; default alpha]: ", spins, "alpha")
        if operation == "frontier":
            show_result(client.orbitals(spin))
        elif operation in {"composition", "cube"}:
            mo = ask("MO [homo/lumo/one-based number; default homo]: ", "homo")
            if operation == "composition":
                method = prompt_choice("Population convention [lowdin/mulliken; default lowdin]: ", ("lowdin", "mulliken"), "lowdin")
                show_result(client.orbital_composition(mo=mo, spin=spin, method=method))
            else:
                output = confirm_output_path(session, "orbital", ".cube")
                if output is not None:
                    show_result(client.orbital_cube(output, mo=mo, spin=spin))
        elif operation in {"dos", "pdos"}:
            show_result(client.dos(spin=spin) if operation == "dos" else client.pdos(spin=spin))
        else:
            utils.print_error("Unknown orbital analysis.")

    def show_vibrations() -> None:
        operations = ["modes"]
        operations.extend(name for name, analysis in (("ir", "ir-spectrum"),
                          ("raman", "raman-spectrum"), ("mode", "normal-mode")) if session.eligible(analysis))
        operation = prompt_choice(f"Vibrational workflow [{'/'.join(operations)}; default modes]: ", tuple(operations), "modes")
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
        operation = prompt_choice(
            "Density/population workflow [integrate/esp/hirshfeld; default integrate]: ",
            ("integrate", "esp", "hirshfeld"), "integrate",
        )
        if operation == "integrate":
            kinds = ("total", "alpha", "beta", "spin") if client.data.spin_density is not None else ("total",)
            kind = prompt_choice(f"Density component [{'/'.join(kinds)}; default total]: ", kinds, "total")
            while True:
                spacing = prompt_positive_float("Grid spacing in bohr [0.15]: ", .15)
                padding = prompt_positive_float("Padding in bohr [6]: ", 6.)
                try:
                    _, shape = molecular_grid_layout(calculation.molecule, spacing_bohr=spacing, padding_bohr=padding)
                except ValueError as exc:
                    print(str(exc))
                    print("Edit spacing/padding or enter back to cancel.")
                    continue
                print(f"Grid: {shape}, {prod(shape):,} points; spacing {spacing:g} bohr, padding {padding:g} bohr.")
                show_result(client.density(kind, spacing_bohr=spacing, padding_bohr=padding))
                break
        elif operation == "esp":
            point = tuple(float(value) for value in ask("ESP coordinates x y z in angstrom [5 0 0]: ", "5 0 0").split())
            component = ask("ESP component [total/electronic/nuclear/mulliken/lowdin; default total]: ", "total")
            show_result(client.esp(point, component=component))
        elif operation == "hirshfeld":
            show_result(client.hirshfeld())
        else:
            utils.print_error("Unknown density/population workflow.")

    def create_report() -> None:
        output = confirm_output_path(session, "report", ".html")
        if output is None:
            return
        show_result(
            build_report_record(
                calculation,
                tuple(name for name in ("summary", "frontier", "mulliken", "lowdin") if session.eligible(name)),
                output,
                "html",
                f"openwfn {filename} report build {output}",
                False,
            )
        )

    def show_bonds() -> None:
        methods = ("geometry", "mayer", "fragments") if session.eligible("mayer") else ("geometry", "fragments")
        method = prompt_choice(f"Bond analysis [{'/'.join(methods)}; default geometry]: ", methods, "geometry")
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
        print(f"\n{PRODUCT_NAME} {__version__} / {menu_filename}")
        if structure is not None:
            formula = client.analyze("summary").data.get("formula", "unknown composition")
            print(f"{formula} · {len(atoms)} centers · "
                  f"charge {structure.charge if structure.charge is not None else 'unknown'} · "
                  f"multiplicity {structure.multiplicity if structure.multiplicity is not None else 'unknown'}")
        else:
            print("Stored volumetric grid; no molecular wavefunction inferred.")

        try:
            raw_choice = prompt_workflow(available_workflows(session))
        except (EOFError, KeyboardInterrupt):
            break
        action = FEATURE_ALIASES.get(raw_choice, raw_choice)

        if action not in {workflow.command for workflow in available_workflows(session)} and action != "q":
            print("That workflow is unavailable for this input; choose a displayed workflow.")
            continue

        if action == "summary":
            nav = run_static_page("Molecular Summary", "A one-page overview of the current molecule.", show_summary)
        elif action == "unavailable":
            for name, capability in session.analyses.items():
                if not capability["available"]:
                    print(f"{name}: missing {', '.join(capability['missing_requirements'])}")
            continue
        elif action == "grid":
            for grid in client.data.grids:
                print(f"Shape: {grid.shape}; origin (angstrom): {grid.origin}; "
                      f"axes (angstrom): {grid.axes}; stored value unit: {grid.value_unit}")
                print("Grid inspection does not establish the physical identity of the stored scalar field.")
            nav = prompt_page_navigation("Stored grid")
        elif action == "properties":
            from .output_properties import read_output
            nav = run_static_page("Source properties", "Properties reported in the source output, not recomputed.",
                                  lambda: show_result(read_output(Path(filename))))
        elif action == "population":
            methods = tuple(name for name in ("mulliken", "lowdin", "hirshfeld") if session.eligible(name))
            def show_population():
                method = prompt_choice(f"Population method [{'/'.join(methods)}]: ", methods, methods[0])
                show_result(client.analyze(method))
            nav = run_static_page("Population analysis", "Charges depend on the selected partitioning convention.", show_population)
        elif action == "excited":
            nav = run_static_page("Excited states", "Source-reported excited states.",
                                  lambda: show_result(client.analyze("excited-states")))
        elif action == "file":
            try:
                new_name = input("Input file (blank to cancel): ").strip()
                if not new_name:
                    continue
                new_session = build_guided_session(Path(new_name))
            except (EOFError, KeyboardInterrupt):
                continue
            except (ValueError, OSError, DataUnavailableError) as exc:
                print(f"Could not open input: {exc}")
                continue
            session = new_session
            client = session.calculation
            filename = session.source
            calculation = client.data.calculation
            structure = client.data.structure
            atoms = structure.coordinates if structure is not None else ()
            atomic_numbers = list(structure.atomic_numbers) if structure is not None else []
            coordinates = list(atoms)
            menu_filename = session.source.name
            continue
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
