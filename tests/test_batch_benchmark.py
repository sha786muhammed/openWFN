import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "benchmark_batch.py"


def test_batch_benchmark_writes_machine_readable_evidence(tmp_path: Path) -> None:
    output = tmp_path / "benchmark.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--count",
            "6",
            "--workers",
            "2",
            "--workspace",
            str(tmp_path / "work"),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        check=False,
    )

    assert result.returncode == 0, result.stderr
    evidence = json.loads(output.read_text(encoding="utf-8"))
    assert evidence["input_count"] == 6
    assert evidence["workers"] == 2
    assert evidence["successes"] == 0
    assert evidence["partial"] == 6
    assert evidence["failures"] == 0
    assert evidence["files_per_second"] > 0
    assert evidence["peak_python_memory_bytes"] > 0
    assert evidence["openwfn_version"]
    assert evidence["python_version"]


def test_batch_benchmark_rejects_non_positive_sizes(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--count",
            "0",
            "--output",
            str(tmp_path / "x.json"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        check=False,
    )

    assert result.returncode == 2
    assert "positive integer" in result.stderr
