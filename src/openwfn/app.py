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

            rendered = render(result, context)
            if context.output_path is not None:
                if context.output_path.exists() and not context.overwrite:
                    raise FileExistsError(
                        f"Output exists: {context.output_path}. Pass --overwrite to replace it."
                    )
                context.output_path.parent.mkdir(parents=True, exist_ok=True)
                context.output_path.write_text(rendered, encoding="utf-8")
                if context.format == "json":
                    context.output_stream.write(rendered)
            elif not context.quiet or context.format == "json":
                context.output_stream.write(rendered)
        if isinstance(result, int):
            return result
        return 1 if isinstance(result, ResultRecord) and result.status == "failed" else 0
    except OpenWFNError as exc:
        _report_failure(exc, context)
        return exc.exit_code
    except FileExistsError as exc:
        message = str(exc).replace("overwrite=True", "--overwrite")
        _report_failure(FileExistsError(message), context)
        return 1
    except Exception as exc:  # application boundary intentionally catches unknown failures
        if context.debug:
            traceback.print_exc(file=context.error_stream)
        _report_failure(exc, context)
        return 1


def _report_failure(exc: Exception, context: CommandContext) -> None:
    if context.format == "json":
        from .presentation import render

        failure = ResultRecord.failure(
            kind="command", analysis_name="command", analysis_version="1",
            exception=exc, elapsed_seconds=0.0,
        )
        context.output_stream.write(render(failure, context))
    else:
        context.error_stream.write(f"Error: {exc}\n")
