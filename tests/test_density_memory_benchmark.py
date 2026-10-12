"""A repeatable memory comparison must retain settings and numeric evidence."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/benchmark_density_integration.py"


def test_density_memory_benchmark_compares_both_paths(tmp_path):
    output = tmp_path / "memory.json"
    subprocess.run([sys.executable, str(SCRIPT), "--inputs", str(ROOT / "examples/water/water.fchk"),
        "--spacing", ".6", "--padding", "1.2", "--output", str(output)], check=True, cwd=ROOT)
    report = json.loads(output.read_text())
    assert report["spacing_bohr"] == .6
    assert report["padding_bohr"] == 1.2
    records = {item["mode"]: item for item in report["records"]}
    assert set(records) == {"streaming", "materialized"}
    assert records["streaming"]["electron_count"] == pytest.approx(
        records["materialized"]["electron_count"], abs=1e-8)
    assert records["streaming"]["input_sha256"] == records["materialized"]["input_sha256"]
    assert report["records"][0]["elapsed_seconds"] >= 0


def test_density_memory_benchmark_does_not_overwrite_report(tmp_path):
    output = tmp_path / "memory.json"
    output.write_text("previous evidence")
    result = subprocess.run([sys.executable, str(SCRIPT), "--output", str(output)],
        capture_output=True, text=True, cwd=ROOT)
    assert result.returncode != 0
    assert "exists" in result.stderr
    assert output.read_text() == "previous evidence"
