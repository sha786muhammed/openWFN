#!/usr/bin/env python3
"""Render README figures from the installed engine and packaged water fixture."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
IMAGE_ROOT = ROOT / "docs/assets/images"
RECORD_ROOT = ROOT / "docs/assets/data/readme-examples"


def run_cli(arguments: list[str], directory: Path) -> str:
    environment = {**os.environ, "NO_COLOR": "1", "TERM": "dumb", "COLUMNS": "96"}
    result = subprocess.run(
        [sys.executable, "-m", "openwfn.cli", *arguments],
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def render_terminal(transcript: str, destination: Path) -> None:
    """Typeset captured stdout; do not invent or replace calculated values."""
    font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
    font = ImageFont.truetype(str(font_path), 21) if font_path.exists() else ImageFont.load_default(size=21)
    title_font = ImageFont.truetype(str(font_path), 25) if font_path.exists() else ImageFont.load_default(size=25)
    lines = [
        wrapped
        for line in transcript.splitlines()
        for wrapped in (textwrap.wrap(line, width=96, subsequent_indent="  ", break_long_words=False) or [""])
    ]
    width = 1320
    line_height = 32
    height = 134 + line_height * len(lines) + 34
    image = Image.new("RGB", (width, height), "#0d1624")
    draw = ImageDraw.Draw(image)
    draw.text((40, 27), "openWFN | packaged water example", font=title_font, fill="#58d5cf")
    draw.line((40, 83, width - 40, 83), fill="#29384b", width=2)
    for index, line in enumerate(lines):
        draw.text((40, 109 + index * line_height), line, font=font, fill="#e8eef7")
    image.save(destination, optimize=True)


def main() -> None:
    IMAGE_ROOT.mkdir(parents=True, exist_ok=True)
    RECORD_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="openwfn-readme-") as temporary:
        directory = Path(temporary)
        run_cli(["examples", "install", "./openwfn-examples"], directory)
        source = "./openwfn-examples/water.fchk"
        arguments = [source, "orbitals", "frontier", "--spin", "all"]
        output = run_cli(arguments, directory)
        transcript = "$ openwfn " + " ".join(arguments) + "\n\n" + output
        (RECORD_ROOT / "water-frontier-cli.txt").write_text(transcript, encoding="utf-8")
        render_terminal(transcript, IMAGE_ROOT / "water-cli-example.png")
        record = json.loads(run_cli(["--format", "json", *arguments], directory))
        (RECORD_ROOT / "water-frontier.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        plot = directory / "water-frontier.png"
        run_cli([source, "plot", "frontier", plot.name], directory)
        (IMAGE_ROOT / "water-frontier-example.png").write_bytes(plot.read_bytes())

    manifest_path = ROOT / "docs/assets/data/asset-provenance.yml"
    manifest = manifest_path.read_text(encoding="utf-8")
    # Replace only entries owned by this generator, retaining all other assets.
    for filename, transformation, alt in (
        ("water-cli-example.png", "Captured plain CLI stdout, line-wrapped and typeset with Pillow; no scientific values changed", "Frontier-orbital CLI output for the packaged water example"),
        ("water-frontier-example.png", "Unmodified PNG written by openwfn plot frontier", "Frontier-orbital plot for the packaged water example"),
    ):
        marker = f"  {filename}:\n"
        if marker in manifest:
            start = manifest.index(marker)
            end = manifest.find("\n  ", start + len(marker))
            # A new top-level asset entry has exactly two leading spaces.
            while end != -1 and manifest[end + 3:end + 4] == " ":
                end = manifest.find("\n  ", end + 1)
            manifest = manifest[:start] + (manifest[end + 1:] if end != -1 else "")
        digest = hashlib.sha256((IMAGE_ROOT / filename).read_bytes()).hexdigest()
        manifest = manifest.rstrip() + "\n" + (
            f"  {filename}:\n"
            "    source: project-created\n"
            "    generation_record: python scripts/render_readme_examples.py using openWFN 0.13.0 and its packaged water.fchk; see docs/guides/readme-examples.md\n"
            f"    sha256: {digest}\n"
            "    license: MIT project asset; input provenance is recorded in examples/PROVENANCE.md\n"
            f"    transformation: {transformation}\n"
            f"    alt: {alt}\n"
        )
    manifest_path.write_text(manifest, encoding="utf-8")
    print("Rendered two README figures and retained the CLI transcript and JSON record.")


if __name__ == "__main__":
    main()
