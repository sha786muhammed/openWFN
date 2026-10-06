"""Compact guided workflow palette."""

from dataclasses import dataclass
from typing import Callable, Sequence


@dataclass(frozen=True, slots=True)
class Workflow:
    label: str
    command: str


WORKFLOWS = (
    Workflow("Inspect molecular structure", "summary"),
    Workflow("Analyze geometry", "geometry"),
    Workflow("Explore bonds and fragments", "bonds"),
    Workflow("Analyze molecular orbitals", "orbitals"),
    Workflow("Analyze vibrations and spectra", "vibrations"),
    Workflow("Calculate density and ESP", "density"),
    Workflow("Open 3D workbench", "workbench"),
    Workflow("Export or convert data", "export"),
    Workflow("Create research report", "report"),
    Workflow("Validate calculation", "validate"),
)


def filter_workflows(workflows: Sequence[Workflow], query: str) -> tuple[Workflow, ...]:
    normalized = query.casefold().strip()
    return tuple(
        workflow
        for workflow in workflows
        if normalized in workflow.label.casefold() or normalized in workflow.command.casefold()
    )


def run_palette(
    header: str,
    prompt: Callable[[Sequence[Workflow]], str],
    dispatch: Callable[[str], int],
) -> int:
    """Select and dispatch one guided workflow using injected terminal I/O."""

    del header
    choice = prompt(WORKFLOWS).strip().casefold()
    if choice in {"q", "quit", "exit"}:
        return 0
    commands = {workflow.command for workflow in WORKFLOWS}
    if choice not in commands:
        return 2
    return dispatch(choice)


def prompt_workflow(workflows: Sequence[Workflow] = WORKFLOWS) -> str:
    """Prompt with arrow-key navigation when questionary is installed."""

    try:
        return terminal_selection('Select a workflow', workflows, cancel='q')
    except ImportError:
        for index, workflow in enumerate(workflows, 1):
            print(f"{index}. {workflow.label} ({workflow.command})")
        try:
            choice = input("Choose a number or command; q to quit > ").strip().casefold()
            if choice.isdigit() and 1 <= int(choice) <= len(workflows):
                return workflows[int(choice) - 1].command
            return choice
        except (EOFError, KeyboardInterrupt):
            return "q"
    except (EOFError, KeyboardInterrupt):
        return 'q'


def terminal_selection(message: str, workflows: Sequence[Workflow], *,
                       default: str | None = None, cancel: str = 'back') -> str:
    """Shared arrow-key selector with an actual Escape binding."""
    import questionary
    from questionary.constants import DEFAULT_STYLE

    from .utils import color_enabled

    choices = [questionary.Choice(workflow.label, value=workflow.command) for workflow in workflows]
    style = None if color_enabled() else questionary.Style([(selector, '') for selector, _ in DEFAULT_STYLE.style_rules])
    question = questionary.select(message, choices=choices, default=default, qmark='❯',
                                 instruction='Up/Down move · Enter select · Esc back · Ctrl+C cancel', style=style)
    @question.application.key_bindings.add('escape')
    def escape(event):
        event.app.exit(result=cancel)
    @question.application.key_bindings.add('c-d')
    def eof(event):
        event.app.exit(exception=EOFError)
    return question.unsafe_ask() or cancel
