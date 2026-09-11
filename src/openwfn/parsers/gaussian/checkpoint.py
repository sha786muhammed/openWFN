"""Safe conversion of binary Gaussian checkpoints with ``formchk``."""

import shutil
import subprocess
from pathlib import Path
from typing import Callable

from ...errors import ExternalProgramError, ParseError


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def resolve_checkpoint(
    path: Path,
    output: Path | None = None,
    runner: Callable[[list[str]], None] = _run,
    executable: str | None = None,
) -> Path:
    """Convert ``path`` to FCHK and return the formatted checkpoint path."""

    if path.suffix.lower() != ".chk":
        raise ParseError("Checkpoint conversion requires a Gaussian .chk input file.")
    output_path = output or path.with_suffix(".fchk")
    if output_path.exists():
        return output_path

    formchk = executable or shutil.which("formchk")
    if formchk is None:
        raise ExternalProgramError(
            "Gaussian checkpoint conversion requires formchk, but it was not found in PATH. "
            "Install Gaussian utilities or run: formchk input.chk output.fchk"
        )
    try:
        runner([formchk, str(path), str(output_path)])
    except (OSError, subprocess.SubprocessError) as exc:
        raise ExternalProgramError(f"formchk failed to convert {path}: {exc}") from exc
    if not output_path.exists():
        raise ExternalProgramError(f"formchk completed without creating {output_path}.")
    return output_path
