import json
import shutil
import subprocess
import sys
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
from .errors import DataUnavailableError, OpenWFNError
from .fchk import print_atom_table  # type: ignore
from .geometry import molecular_formula  # type: ignore
from .guided import (
    GuidedSession,
    available_workflows,
    build_guided_session,
    build_overview,
    inspect_stored_grid,
    reproducible_command,
)
from .guided_exports import ExportLocation, OutputDestination, export_atomically
from .palette import Workflow, prompt_workflow, terminal_selection
from .presentation import render
from .reporting import build_report_record
from .results import ResultRecord
from .services import density_cube_export
from .workbench.export import export_workbench_record
from .xyz import write_xyz

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


class CancelledAction(Exception):
    """Explicit Back/Escape, distinct from a closed input stream."""


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
    if sys.stdin.isatty() and sys.stdout.isatty():
        selected = terminal_selection(prompt, [Workflow(choice, choice) for choice in choices], default=default)
        if selected not in choices:
            raise CancelledAction
        return selected
    while True:
        value = input(prompt).strip().casefold() or default
        if value in choices:
            return value
        if value in {"back", "home", "quit", "exit"}:
            raise CancelledAction
        print("Choose " + ", ".join(choices) + "; or enter back to cancel.")


def prompt_positive_float(prompt: str, default: float) -> float:
    while True:
        value = input(prompt).strip()
        if value.casefold() in {"back", "home", "quit", "exit"}:
            raise CancelledAction
        try:
            number = float(value) if value else default
            if isfinite(number) and number > 0:
                return number
        except ValueError:
            pass
        print("Enter a positive finite number, or back to cancel.")


def confirm_output_path(session: GuidedSession | ExportLocation, label: str, suffix: str) -> OutputDestination | None:
    """Confirm a new destination; input and existing files remain protected."""
    default = session.directory / "results" / f"{session.source.stem}-{label}{suffix}"
    while True:
        try:
            value = input(f"Output path [{default}] (back to cancel): ").strip()
            if value.casefold() in {"back", "home", "quit", "exit"}:
                return None
            path = Path(value).expanduser() if value else default
            if value and path.parent == Path('.'):
                path = session.directory / 'results' / path
            if not path.suffix:
                path = path.with_suffix(suffix)
            if path.suffix.lower() != suffix:
                print(f"This export requires {suffix}; choose another path.")
                continue
            path = path.resolve()
            if path == session.source:
                print("The input file is protected; choose a new output path.")
                continue
            overwrite = path.exists()
            if overwrite:
                if not path.is_file():
                    print('Destination is not a regular file; choose another path.')
                    continue
                if input(f"Replace existing file {path}? Type yes to approve: ").strip().casefold() != 'yes':
                    return None
            print(f"Save to: {path}")
            if input("Confirm save? [y/N]: ").strip().casefold() not in {"y", "yes"}:
                return None
            path.parent.mkdir(parents=True, exist_ok=True)
            return OutputDestination(path, overwrite)
        except (EOFError, KeyboardInterrupt):
            return None
        except OSError as exc:
            print(f"Cannot use that destination: {exc}")


def prompt_indices(labels: tuple[str, ...], *, atom_count: int | None = None) -> list[int] | None:
    """Read a fixed number of 1-based atom indices."""
    values: list[int] = []
    for label in labels:
        value = prompt_int(f"Enter atom {label} (1-based index, blank to cancel): ")
        while value is not None and atom_count is not None and not 1 <= value <= atom_count:
            print(f'Atom number must be between 1 and {atom_count}.')
            value = prompt_int(f"Enter atom {label} (blank to cancel): ")
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

        if choice == 'home':
            return 'home'
        if choice in {"back", "b", "0"}:
            return "back"
        if choice in {"exit", "quit", "x", "q"}:
            return "exit"
        if choice in {'save-json', 'save-csv', 'command', 'details', 'again', 'settings'}:
            return choice
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
    filename = Path(filename).expanduser().resolve()
    if filename.suffix.lower() == '.chk':
        executable = shutil.which('formchk')
        if executable is None:
            print('Binary .chk needs Gaussian formchk in PATH. Convert it to .fchk; pip does not install Gaussian utilities.')
            return 2
        print(f'External converter: {executable}\nOriginal checkpoint: {filename}')
        destination = confirm_output_path(ExportLocation(filename, Path.cwd()), 'converted', '.fchk')
        if destination is None:
            return 0
        def convert(stage):
            subprocess.run([executable, str(filename), str(stage)], check=True)
            build_guided_session(stage, format_hint='fchk')
        try:
            export_atomically(destination, convert)
        except (OpenWFNError, OSError, subprocess.SubprocessError) as exc:
            print(f'Checkpoint conversion failed: {exc}; input preserved.')
            return 2
        except (EOFError, KeyboardInterrupt):
            print('Conversion cancelled; input preserved.')
            return 0
        filename, format_hint = destination.path, 'fchk'
        print(f'Converted FCHK: {filename}')
    session = build_guided_session(Path(filename), format_hint=format_hint)
    client = session.calculation
    calculation = client.data.calculation
    structure = client.data.structure
    atoms = structure.coordinates if structure is not None else ()
    atomic_numbers = list(structure.atomic_numbers) if structure is not None else []
    coordinates = list(atoms)
    menu_filename = str(Path(filename).name)
    last_result = None
    last_arguments = ()

    def show_result(result, arguments=()) -> None:
        nonlocal last_result, last_arguments
        last_result, last_arguments = result, arguments
        print(render(result, CommandContext(input_path=Path(filename), format="plain")), end="")

    def page(title, description, operation):
        nonlocal last_result, last_arguments
        while True:
            last_result, last_arguments = None, ()
            print_feature_page(title, description)
            try:
                operation()
            except EOFError:
                return 'exit'
            except (CancelledAction, KeyboardInterrupt):
                print('\nAction cancelled.')
                return 'home'
            except (OpenWFNError, ValueError, IndexError, OSError) as exc:
                show_result(ResultRecord.failure(kind='guided_workflow', analysis_name=title,
                            analysis_version='1', exception=exc, elapsed_seconds=0.))
            while True:
                actions = ['again/settings', 'back/home', 'quit']
                if last_result is not None:
                    actions.extend(('save-json', 'details'))
                    if last_arguments:
                        actions.append('command')
                    if last_result.kind in {'frontier_orbitals', 'mulliken_population', 'lowdin_population', 'hirshfeld_population'}:
                        actions.append('save-csv')
                print('Result actions: ' + ', '.join(actions))
                if sys.stdin.isatty() and sys.stdout.isatty():
                    options = [Workflow('Back to workflow choices', 'back'), Workflow('Main menu', 'home'),
                               Workflow('Edit settings and run again', 'again'),
                               Workflow('Quit', 'exit')]
                    if last_result is not None:
                        options.extend((Workflow('Save JSON', 'save-json'), Workflow('Details and provenance', 'details')))
                        if last_arguments:
                            options.append(Workflow('Show reproducible command', 'command'))
                        if last_result.kind in {'frontier_orbitals', 'mulliken_population', 'lowdin_population', 'hirshfeld_population'}:
                            options.append(Workflow('Save CSV', 'save-csv'))
                    try:
                        choice = terminal_selection('Result actions', options)
                    except EOFError:
                        return 'exit'
                    except KeyboardInterrupt:
                        return 'back'
                else:
                    choice = prompt_page_navigation(title)
                if choice in {'back', 'home', 'exit'}:
                    return choice
                if choice in {'again', 'settings'}:
                    break
                if last_result is None:
                    print('No structured result to save or inspect.')
                    continue
                if choice == 'details':
                    print(json.dumps(last_result.provenance, indent=2, ensure_ascii=False))
                elif choice == 'command':
                    print(reproducible_command(session, arguments=last_arguments) if last_arguments else
                          'No direct-command equivalent recorded for this action.')
                elif choice in {'save-json', 'save-csv'}:
                    if choice == 'save-csv' and last_result.kind not in {'frontier_orbitals', 'mulliken_population', 'lowdin_population', 'hirshfeld_population'}:
                        print('CSV export is not available for this result; JSON preserves the complete record.')
                        continue
                    suffix = '.json' if choice == 'save-json' else '.csv'
                    destination = confirm_output_path(session, last_result.kind, suffix)
                    if destination is None:
                        continue
                    try:
                        text = render(last_result, CommandContext(format='json' if suffix == '.json' else 'csv'))
                        export_atomically(destination, lambda stage: stage.write_text(text, encoding='utf-8'))
                        print(f'Saved: {destination.path}')
                    except (OSError, ValueError) as exc:
                        print(f'Export failed: {exc}; the previous file was not replaced.')

    def show_summary() -> None:
        show_result(build_overview(session), ('analyze',))

    def show_info() -> None:
        cmd.cmd_info({"Charge": structure.charge, "Multiplicity": structure.multiplicity}, atomic_numbers, coordinates)

    def show_table() -> None:
        utils.print_header("Coordinate Table")
        print_atom_table(atomic_numbers, coordinates)

    def run_distance() -> None:
        show_table()
        indices = prompt_indices(("i", "j"), atom_count=len(atoms))
        if indices is not None:
            show_result(client.geometry_distance(*indices), ('geometry', 'distance', *map(str, indices)))

    def run_angle() -> None:
        show_table()
        indices = prompt_indices(("i", "j", "k"), atom_count=len(atoms))
        if indices is not None:
            show_result(client.geometry_angle(*indices), ('geometry', 'angle', *map(str, indices)))

    def run_dihedral() -> None:
        show_table()
        indices = prompt_indices(("i", "j", "k", "l"), atom_count=len(atoms))
        if indices is not None:
            show_result(client.geometry_dihedral(*indices), ('geometry', 'dihedral', *map(str, indices)))

    def export_xyz() -> None:
        print('XYZ saves elements and coordinates only; charge, multiplicity, basis and ECP information are not preserved.')
        out = confirm_output_path(session, "structure", ".xyz")
        if out:
            export_atomically(out, lambda stage: write_xyz(stage, atomic_numbers, coordinates))
            print(f'Saved: {out.path}')
        else:
            utils.print_warning("Export cancelled.")

    def open_viewer() -> None:
        out = confirm_output_path(session, "workbench", ".html")
        if out:
            open_browser = prompt_open_in_browser()
            show_result(export_atomically(out, lambda stage: export_workbench_record(calculation, stage)),
                        ('workbench', str(out.path)))
            if open_browser:
                import webbrowser

                if not webbrowser.open(out.path.as_uri()):
                    print(f"Browser did not open. The saved file is available at {out.path}.")
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
            show_result(client.orbitals(spin), ('orbitals', 'frontier', '--spin', spin))
        elif operation in {"composition", "cube"}:
            mo = ask("MO [homo/lumo/one-based number; default homo]: ", "homo")
            if operation == "composition":
                method = prompt_choice("Population convention [lowdin/mulliken; default lowdin]: ", ("lowdin", "mulliken"), "lowdin")
                show_result(client.orbital_composition(mo=mo, spin=spin, method=method),
                            ('orbitals', 'composition', '--mo', mo, '--spin', spin, '--method', method))
            else:
                output = confirm_output_path(session, "orbital", ".cube")
                if output is not None:
                    show_result(export_atomically(output, lambda stage: client.orbital_cube(stage, mo=mo, spin=spin)),
                                ('orbitals', 'cube', '--mo', mo, '--spin', spin, '--output', str(output.path)))
        elif operation in {"dos", "pdos"}:
            show_result(client.dos(spin=spin) if operation == "dos" else client.pdos(spin=spin),
                        ('orbitals', operation, '--spin', spin))
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

    def show_density(operation=None, fixed_kind=None) -> None:
        operation = operation or prompt_choice(
            "Density operation [integrate/cube/esp; default integrate]: ",
            ("integrate", "cube", "esp"), "integrate",
        )
        if operation in {"integrate", "cube"}:
            kinds = ("total", "alpha", "beta", "spin") if client.data.spin_density is not None else ("total",)
            kind = fixed_kind or prompt_choice(f"Density component [{'/'.join(kinds)}; default total]: ", kinds, "total")
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
                settings = ('--kind', kind, '--spacing', str(spacing), '--padding', str(padding))
                if operation == 'integrate':
                    show_result(client.density(kind, spacing_bohr=spacing, padding_bohr=padding),
                                ('density', 'integrate', *settings))
                else:
                    destination = confirm_output_path(session, 'density', '.cube')
                    if destination is not None:
                        record = export_atomically(destination, lambda stage: density_cube_export(
                            calculation, kind, spacing, padding, stage, False))
                        from dataclasses import replace
                        record = replace(record, provenance=client.analyze('summary').provenance)
                        show_result(record, ('density', 'cube', str(destination.path), *settings))
                break
        elif operation == "esp":
            point = tuple(float(value) for value in ask("ESP coordinates x y z in angstrom [5 0 0]: ", "5 0 0").split())
            component = ask("ESP component [total/electronic/nuclear/mulliken/lowdin; default total]: ", "total")
            show_result(client.esp(point, component=component),
                        ('esp', 'point', *map(str, point), '--component', component, '--method', 'integrals'))
        elif operation == "hirshfeld":
            show_result(client.hirshfeld())
        else:
            utils.print_error("Unknown density/population workflow.")

    def create_report() -> None:
        output = confirm_output_path(session, "report", ".html")
        if output is None:
            return
        analyses = tuple(name for name in ("summary", "frontier") if session.eligible(name))
        arguments = ('report', 'build', str(output.path), '--analyses', ','.join(analyses))
        show_result(export_atomically(output, lambda stage:
            build_report_record(
                calculation,
                analyses,
                stage,
                "html",
                reproducible_command(session, arguments=arguments),
                False,
            )), arguments)

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

    pending_workflow = None
    while True:
        print(f"\n{PRODUCT_NAME} {__version__} / {menu_filename}")
        provenance = client.data.provenance
        if provenance is not None:
            print(f'Format: {provenance.source_format}; coordinates in angstrom, grid settings in bohr.')
        if structure is not None:
            formula = client.analyze("summary").data.get("formula", "unknown composition")
            print(f"{formula} · {len(atoms)} centers · "
                  f"charge {structure.charge if structure.charge is not None else 'unknown'} · "
                  f"multiplicity {structure.multiplicity if structure.multiplicity is not None else 'unknown'}")
        elif client.data.grids:
            print("Stored volumetric grid; no molecular wavefunction inferred.")
        else:
            print('Source metadata only; atomic structure and wavefunction data are unavailable.')

        try:
            raw_choice = pending_workflow or prompt_workflow(available_workflows(session))
            pending_workflow = None
        except (EOFError, KeyboardInterrupt):
            break
        action = FEATURE_ALIASES.get(raw_choice, raw_choice)

        if action not in {workflow.command for workflow in available_workflows(session)} and action != "q":
            print("That workflow is unavailable for this input; choose a displayed workflow.")
            continue

        if action == "summary":
            nav = page("Molecular Summary", "A one-page overview of the current molecule.", show_summary)
        elif action == "unavailable":
            for name, capability in session.analyses.items():
                if not capability["available"]:
                    print(f"{name}: missing {', '.join(capability['missing_requirements'])}")
            continue
        elif action == "grid":
            def show_grids():
                for grid in client.data.grids:
                    show_result(client._with_provenance(inspect_stored_grid(grid)))
            nav = page('Stored grid', 'Stored-field values and a rectangular-rule mathematical integral; not a reconstructed wavefunction.', show_grids)
        elif action == "properties":
            from .output_properties import read_output
            nav = page("Source properties", "Properties reported in the source output, not recomputed.",
                        lambda: show_result(read_output(Path(filename)), ('properties',)))
        elif action == "population":
            methods = tuple(name for name in ("mulliken", "lowdin", "hirshfeld") if session.eligible(name))
            def show_population():
                method = prompt_choice(f"Population method [{'/'.join(methods)}]: ", methods, methods[0])
                show_result(client.analyze(method), ('population', method))
            nav = page("Population analysis", "Charges depend on the selected partitioning convention.", show_population)
        elif action == "excited":
            nav = page("Excited states", "Source-reported excited states.",
                        lambda: show_result(client.analyze("excited-states"), ('excited', 'states')))
        elif action == "file":
            try:
                new_name = input("Input file (blank to cancel): ").strip()
                if not new_name:
                    continue
                new_session = build_guided_session(Path(new_name))
            except (EOFError, KeyboardInterrupt):
                continue
            except (ValueError, OSError, OpenWFNError) as exc:
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
        elif action == "chat":
            from .assistant_terminal import chat_command
            chat_command(session.source, format_hint=session.format_hint)
            continue
        elif action == "geometry":
            try:
                geometry_choice = input("Geometry command [distance/angle/dihedral/back]: ").strip().casefold()
            except EOFError:
                geometry_choice = "back"
            if geometry_choice in {"distance", "dist"}:
                nav = page("Distance", "Measure the distance between two atoms.", run_distance)
            elif geometry_choice == "angle":
                nav = page("Bond Angle", "Measure an i-j-k bond angle in degrees.", run_angle)
            elif geometry_choice == "dihedral":
                nav = page("Dihedral Angle", "Measure an i-j-k-l torsion angle in degrees.", run_dihedral)
            else:
                continue
        elif action == "export":
            nav = page("Export XYZ", "Write the current coordinates to an XYZ file.", export_xyz)
        elif action == "workbench":
            nav = page(
                "3D Workbench",
                "Export the current molecule to a standalone local HTML workbench.",
                open_viewer,
            )
        elif action == "bonds":
            nav = page("Detected Bonds", "List covalent bonds using tabulated covalent radii.", show_bonds)
        elif action == "orbitals":
            nav = page("Frontier Orbitals", "Report HOMO, LUMO, and energy gap.", show_orbitals)
        elif action == "vibrations":
            nav = page(
                "Vibrational Spectroscopy",
                "Inspect source vibrational modes, IR/Raman spectra, or one normal mode.",
                show_vibrations,
            )
        elif action == 'validate':
            nav = page('Numerical density consistency', 'Electron conservation on the selected grid; this does not establish source convergence.',
                       lambda: show_density('integrate', 'total'))
        elif action == "density":
            nav = page(
                "Density Validation",
                "Integrate total electron density and report conservation error.",
                show_density,
            )
        elif action == "report":
            nav = page(
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
        if nav == 'back' and action in {'orbitals', 'population', 'density', 'vibrations', 'geometry', 'bonds'}:
            pending_workflow = action
