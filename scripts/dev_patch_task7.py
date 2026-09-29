from pathlib import Path

path = Path("src/openwfn/batch.py")
text = path.read_text(encoding="utf-8")

replacements = [
    (
        "from .api import load\nfrom .parsers.registry import DEFAULT_REGISTRY\n",
        "from .api import load\nfrom .formats import path_matches_declared_format\nfrom .parsers.registry import DEFAULT_REGISTRY\n",
    ),
    (
        "        if path.suffix.lower() in supported_suffixes:\n",
        "        if path.suffix.lower() in supported_suffixes or path_matches_declared_format(path):\n",
    ),
    (
        "        provenance = calculation.molecule.provenance\n        checksum = provenance.sha256 if provenance else _file_sha256(path)\n",
        "        provenance = calculation.data.provenance\n        checksum = provenance.sha256 if provenance else _file_sha256(path)\n",
    ),
]

for old, new in replacements:
    if new in text:
        continue
    if old not in text:
        raise SystemExit(f"Task 7 batch patch target missing: {old[:80]!r}")
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
