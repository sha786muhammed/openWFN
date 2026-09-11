#!/usr/bin/env python3
"""Validate public documentation structure, links, metadata, and privacy."""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path
from urllib.parse import unquote

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib

LINK_PATTERN = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")
PRIVATE_PATTERNS = (
    (re.compile(r"/(?:Users|home)/[^/\s]+/"), "local home path"),
    (re.compile(r"Muhammeds-Laptop", re.IGNORECASE), "machine name"),
    (re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"), "private key"),
    (re.compile(r"\bpypi-[A-Za-z0-9_-]{12,}\b"), "PyPI token"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{12,}\b"), "GitHub token"),
)


def iter_markdown(root: Path) -> Iterator[Path]:
    """Yield public Markdown files in stable order."""
    readme = root / "README.md"
    if readme.is_file():
        yield readme
    docs = root / "docs"
    if docs.is_dir():
        yield from sorted(docs.rglob("*.md"))


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def check_internal_links(root: Path, files: Sequence[Path]) -> list[str]:
    """Return findings for unresolved relative Markdown links."""
    findings: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        for raw_target in LINK_PATTERN.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            clean = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not clean:
                continue
            resolved = (path.parent / clean).resolve()
            if resolved.exists():
                pass
            elif clean.endswith("/"):
                resolved = resolved / "index.md"
            elif resolved.suffix == "":
                resolved = resolved.with_suffix(".md")
            if not resolved.exists():
                findings.append(f"{_relative(path, root)}: unresolved link {target}")
    return findings


def check_equation_delimiters(root: Path, files: Sequence[Path]) -> list[str]:
    """Reject delimiters that bypass the configured Arithmatex pipeline."""
    findings: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        if re.search(r"(?m)^\s*\\\[|\\\]\s*$", text):
            findings.append(
                f"{_relative(path, root)}: unsupported equation delimiter; use $$ blocks"
            )
    return findings


def check_release_metadata(root: Path) -> list[str]:
    """Keep explicit README release references aligned with project metadata."""
    readme = root / "README.md"
    project = root / "pyproject.toml"
    if not readme.is_file() or not project.is_file():
        return []
    version = tomllib.loads(project.read_text(encoding="utf-8"))["project"]["version"]
    text = readme.read_text(encoding="utf-8")
    match = re.search(r"openWFN\s+(\d+\.\d+(?:\.\d+)?)", text)
    if match and not version.startswith(match.group(1)):
        return [f"README.md: release {match.group(1)} does not match package {version}"]
    return []


def check_asset_provenance(root: Path) -> list[str]:
    """Require every public raster asset to have a provenance manifest entry."""
    image_root = root / "docs" / "assets" / "images"
    images = [p for p in image_root.glob("*") if p.is_file()] if image_root.is_dir() else []
    if not images:
        return []
    manifest = root / "docs" / "assets" / "data" / "asset-provenance.yml"
    if not manifest.is_file():
        return ["docs/assets/data/asset-provenance.yml: missing asset provenance manifest"]
    text = manifest.read_text(encoding="utf-8")
    return [
        f"{_relative(image, root)}: missing provenance entry"
        for image in images
        if image.name not in text
    ]


def check_private_content(root: Path, files: Sequence[Path]) -> list[str]:
    """Find credentials and machine-specific content in public text files."""
    findings: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        for pattern, label in PRIVATE_PATTERNS:
            if pattern.search(text):
                findings.append(
                    f"{_relative(path, root)}: private or machine-specific content ({label})"
                )
    return findings


def check_page_contract(root: Path, files: Sequence[Path]) -> list[str]:
    """Validate section contracts added as handbook sections are introduced."""
    del root, files
    return []


def collect_findings(root: Path) -> list[str]:
    files = tuple(iter_markdown(root))
    return [
        *check_internal_links(root, files),
        *check_equation_delimiters(root, files),
        *check_release_metadata(root),
        *check_asset_provenance(root),
        *check_private_content(root, files),
        *check_page_contract(root, files),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    root = args.root.resolve()
    findings = collect_findings(root)
    if findings:
        for finding in findings:
            print(finding, file=sys.stderr)
        return 1
    print("documentation checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
