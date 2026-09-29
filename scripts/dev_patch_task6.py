from pathlib import Path

path = Path("src/openwfn/cli.py")
text = path.read_text(encoding="utf-8")

replacements = [
    (
        "from .interactive import run_interactive  # type: ignore\n",
        "from .interactive import run_interactive  # type: ignore\nfrom .inspection import build_capabilities_result\n",
    ),
    (
        '            "openWFN — reproducible Gaussian wavefunction analysis, reporting, "\n            "and offline molecular visualization."\n',
        '            "openWFN — reproducible wavefunction and scientific post-processing "\n            "across supported quantum-chemistry formats."\n',
    ),
    (
        '    subparsers.add_parser("doctor", help="Inspect parsed data and available analysis capabilities")\n',
        '    subparsers.add_parser("capabilities", help="Report normalized data and analysis capabilities")\n    subparsers.add_parser("doctor", help="Inspect parsed data and available analysis capabilities")\n',
    ),
    (
        '    if args.command == "doctor":\n        return execute(lambda: _doctor_result(Path(args.file)), _context(args))\n',
        '    if args.command == "capabilities":\n        return execute(lambda: build_capabilities_result(Path(args.file)), _context(args))\n\n    if args.command == "doctor":\n        return execute(lambda: _doctor_result(Path(args.file)), _context(args))\n',
    ),
]

for old, new in replacements:
    if new in text:
        continue
    if old not in text:
        raise SystemExit(f"Task 6 CLI patch target missing: {old[:80]!r}")
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
