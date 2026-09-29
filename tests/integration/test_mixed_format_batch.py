import importlib.util
from pathlib import Path

import pytest

from openwfn.batch import discover_inputs, run_batch

ROOT = Path(__file__).resolve().parents[2]
WATER_FCHK = ROOT / "examples" / "water" / "water.fchk"


def test_discover_inputs_accepts_interop_patterns_and_ambiguous_outputs(tmp_path: Path) -> None:
    paths = [
        tmp_path / "sample.molden",
        tmp_path / "sample.wfx",
        tmp_path / "POSCAR",
        tmp_path / "calculation.out",
        tmp_path / "notes.txt",
    ]
    for path in paths:
        path.write_text("synthetic\n", encoding="utf-8")

    discovery = discover_inputs([tmp_path])

    assert {path.name for path in discovery.inputs} == {
        "sample.molden",
        "sample.wfx",
        "POSCAR",
        "calculation.out",
    }
    assert tuple(path.name for path in discovery.unsupported) == ("notes.txt",)


def test_mixed_batch_continues_and_preserves_unsupported_analysis_record(tmp_path: Path) -> None:
    structure = tmp_path / "structure.xyz"
    structure.write_text(
        "3\nwater\nO 0 0 0\nH 0.7586 0 0.5043\nH -0.7586 0 0.5043\n",
        encoding="utf-8",
    )
    output = tmp_path / "results"

    manifest = run_batch(
        [WATER_FCHK, structure],
        operation=None,
        workers=1,
        output_dir=output,
        analyses=("frontier",),
    )

    assert len(manifest.records) == 2
    by_name = {Path(record.input_path).name: record for record in manifest.records}
    assert by_name["water.fchk"].status == "success"

    unsupported = by_name["structure.xyz"]
    assert unsupported.status == "error"
    assert unsupported.input_sha256
    assert len(unsupported.results) == 1
    assert unsupported.results[0].status == "failed"
    assert unsupported.results[0].validation_status == "Unsupported"
    assert unsupported.results[0].error is not None
    assert unsupported.results[0].error.category == "DataUnavailableError"
    assert "alpha orbitals" in unsupported.results[0].error.message.lower()

    assert (output / "batch-manifest.json").is_file()
    assert (output / "batch-summary.csv").is_file()


def test_process_pool_missing_backend_isolated_to_backend_record(tmp_path: Path) -> None:
    if importlib.util.find_spec("iodata") is not None:
        pytest.skip("core-only missing-backend contract runs only when IOData is absent")

    backend_only = tmp_path / "sample.molden"
    backend_only.write_text("[Molden Format]\n[Title]\nsynthetic\n", encoding="utf-8")
    output = tmp_path / "parallel-results"

    manifest = run_batch(
        [WATER_FCHK, backend_only],
        operation=None,
        workers=2,
        output_dir=output,
        analyses=("summary",),
    )

    by_name = {Path(record.input_path).name: record for record in manifest.records}
    assert by_name["water.fchk"].status == "success"
    missing = by_name["sample.molden"]
    assert missing.status == "error"
    assert missing.error is not None
    assert "openwfn[interop]" in missing.error
    assert "ModuleNotFoundError" not in missing.error
