"""Deterministic multi-input analysis runner."""

import json
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from .api import load


@dataclass(frozen=True, slots=True)
class BatchRecord:
    input_path: str
    status: Literal["success", "error"]
    result: dict[str, object] | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class BatchManifest:
    operation: str
    records: tuple[BatchRecord, ...]


def _run_one(arguments: tuple[Path, str]) -> BatchRecord:
    path, operation = arguments
    try:
        calculation = load(path)
        if operation != "summary":
            raise ValueError(f"Unsupported batch operation: {operation}")
        return BatchRecord(str(path), "success", result=calculation.analyze_geometry())
    except Exception as exc:
        return BatchRecord(str(path), "error", error=str(exc))


def run_batch(
    inputs: list[Path],
    operation: str,
    workers: int,
    output_dir: Path,
    fail_fast: bool = False,
) -> BatchManifest:
    if workers < 1:
        raise ValueError("workers must be at least one")
    arguments = [(Path(path), operation) for path in inputs]
    records: list[BatchRecord] = []
    if workers == 1 or fail_fast:
        for argument in arguments:
            record = _run_one(argument)
            records.append(record)
            if fail_fast and record.status == "error":
                break
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            records.extend(executor.map(_run_one, arguments))

    manifest = BatchManifest(operation=operation, records=tuple(records))
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {"operation": operation, "records": [asdict(record) for record in records]}
    (output_dir / "batch-manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest
