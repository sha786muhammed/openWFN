"""Synchronize release-facing metadata from pyproject.toml."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


VERSION_PATTERN = re.compile(r"(?m)^version:\s*[^\r\n]+$")
DATE_PATTERN = re.compile(r"(?m)^date-released:\s*[^\r\n]+$")
URL_PATTERN = re.compile(r"(?m)^url:\s*[^\r\n]+$")


def read_project_version(project_file: Path) -> str:
    """Return the authoritative project version."""
    with project_file.open("rb") as stream:
        return str(tomllib.load(stream)["project"]["version"])


def read_repository_url(project_file: Path) -> str:
    """Return the authoritative source repository URL."""
    with project_file.open("rb") as stream:
        return str(tomllib.load(stream)["project"]["urls"]["Repository"])


def read_release_date(changelog_file: Path, release_version: str) -> str:
    """Return the recorded changelog date for a release version."""
    changelog = changelog_file.read_text(encoding="utf-8")
    match = re.search(
        rf"(?m)^## \[{re.escape(release_version)}\] - ([0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}})$",
        changelog,
    )
    if match is None:
        raise ValueError(f"CHANGELOG.md has no dated entry for {release_version}")
    return match.group(1)


def rendered_citation(
    citation_text: str,
    release_version: str,
    release_date: str,
    release_url: str,
) -> str:
    """Render citation metadata with synchronized release fields."""
    version_matches = VERSION_PATTERN.findall(citation_text)
    date_matches = DATE_PATTERN.findall(citation_text)
    url_matches = URL_PATTERN.findall(citation_text)
    if len(version_matches) != 1 or len(date_matches) != 1 or len(url_matches) != 1:
        raise ValueError(
            "CITATION.cff must contain one version, date-released, and url field"
        )

    rendered = VERSION_PATTERN.sub(f'version: "{release_version}"', citation_text)
    rendered = DATE_PATTERN.sub(f"date-released: {release_date}", rendered)
    rendered = URL_PATTERN.sub(f'url: "{release_url}"', rendered)
    return rendered


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check without writing")
    parser.add_argument("--date", help="release date in YYYY-MM-DD format")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    project_file = root / "pyproject.toml"
    citation_file = root / "CITATION.cff"
    changelog_file = root / "CHANGELOG.md"

    try:
        current = citation_file.read_text(encoding="utf-8")
        release_version = read_project_version(project_file)
        release_date = args.date or read_release_date(changelog_file, release_version)
        release_url = f"{read_repository_url(project_file)}/releases/tag/v{release_version}"
        expected = rendered_citation(
            current,
            release_version,
            release_date,
            release_url,
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
