"""Parallel batch scheduling must respect a conservative memory estimate."""

import json
from pathlib import Path

import pytest

from openwfn import batch


@pytest.mark.parametrize("available,wanted", [(1024**3, 1), (4 * 1024**3, 6), (None, 1)])
def test_batch_workers_are_bounded_by_available_memory(available, wanted, tmp_path, monkeypatch):
    choose = getattr(batch, "_bounded_workers", None)
    assert callable(choose), "Batch needs a memory-aware worker decision"
    paths = []
    for index in range(8):
        path = tmp_path / f"{index}.xyz"
        path.write_text("1\nH\nH 0 0 0\n")
        paths.append(path)
    monkeypatch.setattr(batch, "_available_memory_bytes", lambda: available)
    effective, warnings = choose(8, paths)
    assert effective == wanted
    assert warnings


def test_low_memory_batch_uses_serial_path_and_preserves_results(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, "_available_memory_bytes", lambda: 1024**3, raising=False)

    def forbidden(*args, **kwargs):
        raise AssertionError("Parallel workers started beyond available memory")

    monkeypatch.setattr(batch, "_run_parallel", forbidden)
    sources = []
    for index in range(2):
        path = tmp_path / f"{index}.xyz"
        path.write_text("1\nH\nH 0 0 0\n")
        sources.append(path)
    result = batch.run_batch(sources, "summary", 8, tmp_path / "results")
    assert len(result.records) == 2
    assert all(record.status != "error" for record in result.records)
    assert result.requested_workers == 8
    assert result.effective_workers == 1
    assert result.resource_warnings
    saved = json.loads((tmp_path / "results/batch-manifest.json").read_text())
    assert saved["effective_workers"] == 1
    assert saved["requested_workers"] == 8
    assert saved["resource_warnings"]


def test_missing_batch_input_still_reaches_per_file_error(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, "_available_memory_bytes", lambda: 4 * 1024**3)
    source = tmp_path / "good.xyz"
    source.write_text("1\nH\nH 0 0 0\n")
    effective, _ = batch._bounded_workers(2, [source, tmp_path / "missing.xyz"])
    assert 1 <= effective <= 2


@pytest.mark.parametrize("workers", [True, 0, -1, 1.5])
def test_batch_rejects_invalid_worker_counts(workers, tmp_path):
    with pytest.raises(ValueError, match="workers"):
        batch.run_batch([Path("missing.xyz")], "summary", workers, tmp_path)
