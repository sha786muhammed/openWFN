from pathlib import Path

from openwfn.parsers.registry import load
from openwfn.workbench.export import export_workbench

ROOT = Path(__file__).resolve().parents[1]
WATER = ROOT / "examples" / "water" / "water.fchk"


def test_workbench_preserves_javascript_newline_escape(tmp_path: Path) -> None:
    output = tmp_path / "water-workbench.html"
    calculation = load(WATER)

    export_workbench(calculation, output)

    html = output.read_text(encoding="utf-8")
    assert ".join('\\n')" in html
    assert ".join('\n')" not in html
