"""Application boundary shared by the CLI and guided interface."""

import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal, TextIO

from .errors import OpenWFNError
from .results import ResultRecord

OutputFormat = Literal["table", "plain", "json", "csv"]


@dataclass(slots=True)
class CommandContext:
    input_path: Path | None = None
    output_path: Path | None = None
    format: OutputFormat = "table"
    color: bool = True
    quiet: bool = False
    verbose: bool = False
    debug: bool = False
    compact: bool = False
    overwrite: bool = False
    output_stream: TextIO = field(default_factory=lambda: sys.stdout)
    error_stream: TextIO = field(default_factory=lambda: sys.stderr)


def execute(operation: Callable[[], ResultRecord | int | None], context: CommandContext) -> int:
    """Execute one operation and translate expected failures to stable exit codes."""

    try:
        result = operation()
        if isinstance(result, ResultRecord):
            from .presentation import render

            context.output_stream.write(render(result, context))
        return result if isinstance(result, int) else 0
    except OpenWFNError as exc:
        context.error_stream.write(f"Error: {exc}\n")
        return exc.exit_code
    except Exception as exc:  # application boundary intentionally catches unknown failures
        if context.debug:
            traceback.print_exc(file=context.error_stream)
        else:
            context.error_stream.write(f"Error: {exc}\n")
        return 1
