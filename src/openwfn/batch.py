"""Deterministic multi-input analysis runner."""

import json
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Literal

from .analysis.registry import available_analyses, run_analysis_safe
from .api import load
from .results import ResultRecord

BATCH_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True, slots=True)
class BatchRecord:
    input_path: str
    status: Literal["success", "partial", "error"]
    result: dict[str, object] | None = None
    error: str | None = None
    input_sha256: str | None = None
    results: tuple[ResultRecord, ...] = ()


@dataclass(frozen=True, slots=True)
class BatchManifest:
    operation: str
    records: tuple[BatchRecord, ...]
    analyses: tuple[str, ...] = ()
    schema_version: str = field(default=BATCH_SCHEMA_VERSION, init=False)


def _file_sha256(path: Path) -> str | None:
    try:
        return sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _run_one(arguments: tuple[Path, tuple[str, ...]]) -> BatchRecord:
    path, analyses = arguments
    try:
        calculation = load(path)
        results = tuple(run_analysis_safe(calculation.data, name) for name in analyses)
        successful = [result for result in results if result.status == "success"]
        if len(successful) == len(results):
            status = "success"
        elif successful:
            status = "partial"
        else:
            status = "error"
        provenance = calculation.molecule.provenance
        checksum = provenance.sha256 if provenance else _file_sha256(path)
        errors = [result.error.message for result in results if result.error]
        return BatchRecord(
            input_path=str(path),
            status=status,
            result=successful[0].data if successful else None,
            error="; ".join(errors) if status == "error" else None,
            input_sha256=checksum,
            results=results,
        )
    except Exception as exc:
        return BatchRecord(
            str(path),
            "error",
            error=str(exc),
            input_sha256=_file_sha256(path),
        )


def _record_payload(record: BatchRecord) -> dict[str, object]:
    return {
        "error": record.error,
        "input_path": record.input_path,
        "input_sha256": record.input_sha256,
        "result": record.result,
        "results": [result.as_dict() for result in record.results],
        "status": record.status,
    }


def run_batch(
    inputs: list[Path],
    operation: str | None,
    workers: int,
    output_dir: Path,
    fail_fast: bool = False,
    *,
    analyses: tuple[str, ...] | None = None,
) -> BatchManifest:
    if workers < 1:
        raise ValueError("workers must be at least one")
    requested = analyses if analyses is not None else ((operation or "summary"),)
    normalized = tuple(dict.fromkeys(name.strip().lower() for name in requested if name.strip()))
    if not normalized:
        raise ValueError("at least one analysis is required")
    supported = available_analyses()
    unknown = tuple(name for name in normalized if name not in supported)
    if unknown:
        raise ValueError(
            f"Unknown batch analyses: {', '.join(unknown)}. Available analyses: "
            f"{', '.join(supported)}"
        )
    arguments = [(Path(path), normalized) for path in inputs]
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

    operation_name = normalized[0] if len(normalized) == 1 else "multiple"
    manifest = BatchManifest(
        operation=operation_name,
        records=tuple(records),
        analyses=normalized,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "analyses": list(normalized),
        "operation": operation_name,
        "records": [_record_payload(record) for record in records],
        "schema_version": BATCH_SCHEMA_VERSION,
    }
    (output_dir / "batch-manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest
