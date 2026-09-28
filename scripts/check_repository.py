#!/usr/bin/env python3
"""Check repository policy, metadata, provenance, and local editable-install state."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterator, Sequence
from importlib.metadata import distributions
from pathlib import Path
from urllib.parse import unquote, urlparse

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib


REQUIRED_FILES = (
    "CITATION.cff",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "CONTRIBUTORS.md",
    "LICENSE",
    "MAINTAINERS.md",
    "ROADMAP.md",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "examples/PROVENANCE.md",
    "docs/assets/data/asset-provenance.yml",
    "src/openwfn/assets/3Dmol-min.js.LICENSE.txt",
)
PUBLIC_SUFFIXES = {".md", ".toml", ".yml", ".yaml"}
INTERNAL_BRANDS = ("Chat" + "GPT", "Co" + "dex", "Clau" + "de")
PRIVATE_PATTERNS = (
    re.compile(r"/(?:Users|home)/[^/\s]+/"),
    re.compile(rf"\b{'NASA' + 'KY'}\b", re.IGNORECASE),
    re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
    re.compile(r"\bpypi-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{12,}\b"),
)
REINSTALL = "python -m pip install --no-build-isolation -e ."


def project_version(root: Path) -> str:
    """Read the authoritative package version."""
    with (root / "pyproject.toml").open("rb") as stream:
        return str(tomllib.load(stream)["project"]["version"])


def _metadata_version(package_info: Path) -> str | None:
    match = re.search(
        r"(?m)^Version:\s*(\S+)\s*$", package_info.read_text(encoding="utf-8")
    )
    return match.group(1) if match else None


def check_local_egg_info(root: Path, expected_version: str) -> list[str]:
    """Report stale source-tree distribution metadata without changing it."""
    findings: list[str] = []
    candidates = sorted((root / "src").glob("*.egg-info/PKG-INFO"))
    candidates.extend(sorted(root.glob("*.egg-info/PKG-INFO")))
    for package_info in candidates:
        found = _metadata_version(package_info)
        if found != expected_version:
            relative = package_info.relative_to(root).as_posix()
            findings.append(
                f"{relative}: expected {expected_version}, found {found or 'no Version field'}; "
                f"inspect ignored metadata and reinstall with `{REINSTALL}`"
            )
    return findings


def discover_editable_installs() -> tuple[tuple[str, Path], ...]:
    """Return installed editable openwfn versions and source directories."""
    records: list[tuple[str, Path]] = []
    for distribution in distributions(name="openwfn"):
        direct_url = distribution.read_text("direct_url.json")
        if not direct_url:
            continue
        try:
            record = json.loads(direct_url)
        except json.JSONDecodeError:
            continue
        if not record.get("dir_info", {}).get("editable"):
            continue
        parsed = urlparse(str(record.get("url", "")))
        if parsed.scheme != "file":
            continue
        source = Path(unquote(parsed.path)).resolve()
        records.append((str(distribution.version), source))
    return tuple(records)


def check_editable_installs(
    root: Path,
    expected_version: str,
    editable_installs: Sequence[tuple[str, Path]],
) -> list[str]:
    """Report editable distributions that disagree with this checkout."""
    findings: list[str] = []
    expected_source = root.resolve()
    for found_version, found_source in editable_installs:
        source = found_source.resolve()
        problems: list[str] = []
        if found_version != expected_version:
            problems.append(f"expected {expected_version}, found {found_version}")
        if source != expected_source:
            problems.append(f"expected source {expected_source}, found source {source}")
        if problems:
            findings.append(
                "editable openwfn metadata: "
                + "; ".join(problems)
                + f"; reinstall from this checkout with `{REINSTALL}`"
            )
    return findings


def iter_public_text(root: Path) -> Iterator[Path]:
    """Yield tracked-style public text while ignoring generated and environment trees."""
    ignored_parts = {".git", ".venv", ".worktrees", "build", "dist", "site"}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in PUBLIC_SUFFIXES:
            continue
        if any(part in ignored_parts for part in path.relative_to(root).parts):
            continue
        yield path


def check_public_text(root: Path) -> list[str]:
    """Reject private-machine content, credentials, and internal branding."""
    findings: list[str] = []
    for path in iter_public_text(root):
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(brand.lower() in text.lower() for brand in INTERNAL_BRANDS):
            findings.append(f"{relative}: internal assistant branding")
        if any(pattern.search(text) for pattern in PRIVATE_PATTERNS):
            findings.append(f"{relative}: private path, host name, or credential-like content")
    return findings


def collect_findings(
    root: Path,
    *,
    editable_installs: Sequence[tuple[str, Path]] | None = None,
) -> list[str]:
    """Collect every repository finding without modifying the checkout."""
    root = root.resolve()
    expected_version = project_version(root)
    installed = discover_editable_installs() if editable_installs is None else editable_installs
    findings = [
        f"missing required file: {relative}"
        for relative in REQUIRED_FILES
        if not (root / relative).is_file()
    ]
    findings.extend(check_local_egg_info(root, expected_version))
    findings.extend(check_editable_installs(root, expected_version, installed))
    findings.extend(check_public_text(root))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        findings = collect_findings(args.root)
    except (KeyError, OSError, ValueError) as exc:
        print(f"repository preflight error: {exc}", file=sys.stderr)
        return 2
    if findings:
        for finding in findings:
            print(finding, file=sys.stderr)
        return 1
    print("repository preflight passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
