"""Extensible parser dispatch by normalized filename suffix."""

from pathlib import Path
from typing import Any, Callable

from ..errors import ParseError
from .gaussian.checkpoint import resolve_checkpoint
from .gaussian.cube import parse_cube
from .gaussian.fchk import parse_fchk
from .gaussian.output import parse_gaussian_output
from .mol import parse_mol
from .pdb import parse_pdb
from .sdf import parse_sdf
from .xyz import parse_xyz

Parser = Callable[[Path], Any]


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: dict[str, Parser] = {}

    def register(self, suffixes: tuple[str, ...], parser: Parser) -> None:
        for suffix in suffixes:
            self._parsers[suffix.lower() if suffix.startswith(".") else f".{suffix.lower()}"] = parser

    def load(self, path: Path) -> Any:
        suffix = path.suffix.lower()
        parser = self._parsers.get(suffix)
        if parser is None:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            try:
                xyz_count = int(lines[0].strip())
            except (IndexError, ValueError):
                xyz_count = -1
            if xyz_count > 0 and len(lines) == xyz_count + 2:
                parser = parse_xyz
            else:
                raise ParseError(f"Unsupported input format '{suffix}' for {path.name}.")
        return parser(path)


DEFAULT_REGISTRY = ParserRegistry()
DEFAULT_REGISTRY.register((".fchk", ".fch"), parse_fchk)
DEFAULT_REGISTRY.register((".chk",), lambda path: parse_fchk(resolve_checkpoint(path)))
DEFAULT_REGISTRY.register((".cube", ".cub"), parse_cube)
DEFAULT_REGISTRY.register((".log", ".out"), parse_gaussian_output)
DEFAULT_REGISTRY.register((".xyz",), parse_xyz)
DEFAULT_REGISTRY.register((".pdb",), parse_pdb)
DEFAULT_REGISTRY.register((".mol",), parse_mol)
DEFAULT_REGISTRY.register((".sdf",), parse_sdf)


def load(path: Path) -> Any:
    return DEFAULT_REGISTRY.load(path)
