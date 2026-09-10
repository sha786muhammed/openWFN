"""Synchronize release-facing metadata from pyproject.toml."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


VERSION_PATTERN = re.compile(r"(?m)^version:\s*[^\r\n]+$")
DATE_PATTERN = re.compile(r"(?m)^date-released:\s*[^\r\n]+$")


def read_project_version(project_file: Path) -> str:
    """Return the authoritative project version."""
    with project_file.open("rb") as stream:
        return str(tomllib.load(stream)["project"]["version"])


def rendered_citation(
    citation_text: str,
    release_version: str,
    release_date: str | None,
) -> str:
    """Render citation metadata with synchronized release fields."""
    version_matches = VERSION_PATTERN.findall(citation_text)
    date_matches = DATE_PATTERN.findall(citation_text)
    if len(version_matches) != 1 or len(date_matches) != 1:
        raise ValueError("CITATION.cff must contain one version and one date-released field")

    rendered = VERSION_PATTERN.sub(f'version: "{release_version}"', citation_text)
    if release_date is not None:
        rendered = DATE_PATTERN.sub(f"date-released: {release_date}", rendered)
    return rendered


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check without writing")
    parser.add_argument("--date", help="release date in YYYY-MM-DD format")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    project_file = root / "pyproject.toml"
    citation_file = root / "CITATION.cff"

    try:
        current = citation_file.read_text(encoding="utf-8")
        expected = rendered_citation(
            current,
            read_project_version(project_file),
            args.date,
        )
    except (KeyError, OSError, ValueError) as exc:
        print(f"release metadata error: {exc}", file=sys.stderr)
        return 2

    if args.check:
        if current != expected:
            print("CITATION.cff is not synchronized with pyproject.toml", file=sys.stderr)
            return 1
        return 0

    citation_file.write_text(expected, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
