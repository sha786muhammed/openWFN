"""Confirmed destinations and interruption-safe guided exports."""

import os
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, TypeVar

from .results import ResultRecord

T = TypeVar('T')


@dataclass(frozen=True)
class OutputDestination:
    path: Path
    overwrite: bool = False


@dataclass(frozen=True)
class ExportLocation:
    source: Path
    directory: Path


def export_atomically(destination: OutputDestination, writer: Callable[[Path], T]) -> T:
    """Publish only a complete export; unapproved replacement is race-safe."""
    path = destination.path
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.openwfn-export-', dir=path.parent) as directory:
        stage = Path(directory) / path.name
        result = writer(stage)
        if not stage.is_file():
            raise OSError('Exporter did not produce a complete file.')
        if destination.overwrite:
            os.replace(stage, path)
        else:
            os.link(stage, path)
        if isinstance(result, ResultRecord):
            result = replace(result, data={**result.data, 'output': str(path)})
        return result
