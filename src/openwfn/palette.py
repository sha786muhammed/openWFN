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
        import questionary

        choices = [questionary.Choice(workflow.label, value=workflow.command) for workflow in workflows]
        if not any(workflow.command in {"q", "exit"} for workflow in workflows):
            choices.append(questionary.Choice("Quit", value="q"))
        selected = questionary.select(
            "Select a workflow",
            choices=choices,
            qmark="❯",
        ).ask()
        return selected or "q"
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
