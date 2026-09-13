"""Deterministic multi-input analysis runner."""

import csv
import io
import json
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field, replace
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Literal, cast

from .analysis.registry import available_analyses, run_analysis_safe
from .api import load
from .parsers.registry import DEFAULT_REGISTRY
from .results import RESULT_SCHEMA_VERSION, ResultRecord

BATCH_SCHEMA_VERSION = "1.0"
ProgressCallback = Callable[[int, int, "BatchRecord"], None]


@dataclass(frozen=True, slots=True)
class InputDiscovery:
    inputs: tuple[Path, ...]
    unsupported: tuple[Path, ...] = ()


@dataclass(frozen=True, slots=True)
class BatchRecord:
    input_path: str
    status: Literal["success", "partial", "error"]
    result: dict[str, object] | None = None
    error: str | None = None
    input_sha256: str | None = None
    results: tuple[ResultRecord, ...] = ()
    skipped: bool = False


@dataclass(frozen=True, slots=True)
class BatchManifest:
    operation: str
    records: tuple[BatchRecord, ...]
    analyses: tuple[str, ...] = ()
    configuration_fingerprint: str = ""
    unsupported_inputs: tuple[str, ...] = ()
    schema_version: str = field(default=BATCH_SCHEMA_VERSION, init=False)


def _inside(path: Path, directory: Path | None) -> bool:
    if directory is None:
        return False
    try:
        path.resolve().relative_to(directory.resolve())
    except ValueError:
        return False
    return True


def discover_inputs(
    inputs: list[Path],
    *,
    recursive: bool = False,
    output_dir: Path | None = None,
) -> InputDiscovery:
    """Expand files and directories into supported, deduplicated inputs."""

    supported_suffixes = set(DEFAULT_REGISTRY.supported_suffixes())
    discovered: list[Path] = []
    unsupported: list[Path] = []
    seen: set[Path] = set()
    unsupported_seen: set[Path] = set()

    def add(path: Path) -> None:
        identity = path.resolve()
        if identity in seen or identity in unsupported_seen or _inside(path, output_dir):
            return
        if path.suffix.lower() in supported_suffixes:
            seen.add(identity)
            discovered.append(path)
        else:
            unsupported_seen.add(identity)
            unsupported.append(path)

    for supplied in inputs:
        path = Path(supplied)
        if path.is_dir():
            candidates = path.rglob("*") if recursive else path.iterdir()
            files = [candidate for candidate in candidates if candidate.is_file()]
            files.sort(
                key=lambda candidate: (
                    len(candidate.relative_to(path).parts),
                    str(candidate.relative_to(path)).casefold(),
                )
            )
            for candidate in files:
                add(candidate)
        else:
            add(path)
    return InputDiscovery(tuple(discovered), tuple(unsupported))


def _file_sha256(path: Path) -> str | None:
    try:
        digest = sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _configuration_fingerprint(analyses: tuple[str, ...]) -> str:
    payload = json.dumps(
        {
            "analyses": list(analyses),
            "batch_schema_version": BATCH_SCHEMA_VERSION,
            "result_schema_version": RESULT_SCHEMA_VERSION,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def _record_path(output_dir: Path, input_path: Path) -> Path:
    identity = sha256(str(input_path.resolve()).encode("utf-8")).hexdigest()[:16]
    return output_dir / "records" / f"{input_path.stem}-{identity}.json"


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


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
        "skipped": record.skipped,
        "status": record.status,
    }


def _record_from_payload(payload: dict[str, Any]) -> BatchRecord:
    return BatchRecord(
        input_path=str(payload["input_path"]),
        status=cast(Literal["success", "partial", "error"], payload["status"]),
        result=payload.get("result"),
        error=payload.get("error"),
        input_sha256=payload.get("input_sha256"),
        results=tuple(ResultRecord.from_dict(item) for item in payload.get("results", ())),
        skipped=bool(payload.get("skipped", False)),
    )


def _load_completed_record(
    path: Path,
    output_dir: Path,
    input_sha256: str | None,
    configuration_fingerprint: str,
) -> BatchRecord | None:
    saved_path = _record_path(output_dir, path)
    try:
        payload = json.loads(saved_path.read_text(encoding="utf-8"))
        record = _record_from_payload(payload["record"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if payload.get("schema_version") != BATCH_SCHEMA_VERSION:
        return None
    if payload.get("configuration_fingerprint") != configuration_fingerprint:
        return None
    if Path(record.input_path).resolve() != path.resolve():
        return None
    if record.input_sha256 != input_sha256 or record.status == "error":
        return None
    return replace(record, skipped=True)


def _write_record(
    record: BatchRecord,
    path: Path,
    output_dir: Path,
    configuration_fingerprint: str,
) -> None:
    _atomic_write_json(
        _record_path(output_dir, path),
        {
            "configuration_fingerprint": configuration_fingerprint,
            "record": _record_payload(record),
            "schema_version": BATCH_SCHEMA_VERSION,
        },
    )


def _write_csv_index(records: list[BatchRecord], output_dir: Path) -> None:
    stream = io.StringIO()
    fields = (
        "input_path",
        "input_sha256",
        "status",
        "skipped",
        "analysis_successes",
        "analysis_failures",
        "elapsed_seconds",
        "error",
    )
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for record in records:
        successes = sum(result.status == "success" for result in record.results)
        failures = sum(result.status == "failed" for result in record.results)
        elapsed = sum(result.elapsed_seconds or 0.0 for result in record.results)
        result_errors = [result.error.message for result in record.results if result.error]
        writer.writerow(
            {
                "input_path": record.input_path,
                "input_sha256": record.input_sha256 or "",
                "status": record.status,
                "skipped": str(record.skipped).lower(),
                "analysis_successes": successes,
                "analysis_failures": failures,
                "elapsed_seconds": f"{elapsed:.9f}",
                "error": record.error or "; ".join(result_errors),
            }
        )
    _atomic_write_text(output_dir / "batch-summary.csv", stream.getvalue())


def run_batch(
    inputs: list[Path],
    operation: str | None,
    workers: int,
    output_dir: Path,
    fail_fast: bool = False,
    *,
    analyses: tuple[str, ...] | None = None,
    resume: bool = False,
    recursive: bool = False,
    progress: ProgressCallback | None = None,
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
    discovery = discover_inputs(inputs, recursive=recursive, output_dir=output_dir)
    paths = list(discovery.inputs)
    if not paths:
        raise ValueError("no supported input files were discovered")
    fingerprint = _configuration_fingerprint(normalized)
    records_by_index: dict[int, BatchRecord] = {}
    pending: list[tuple[int, tuple[Path, tuple[str, ...]]]] = []
    completed_count = 0
    for index, path in enumerate(paths):
        cached = (
            _load_completed_record(path, output_dir, _file_sha256(path), fingerprint)
            if resume
            else None
        )
        if cached is not None:
            records_by_index[index] = cached
            completed_count += 1
            if progress is not None:
                progress(completed_count, len(paths), cached)
        else:
            pending.append((index, (path, normalized)))

    if workers == 1 or fail_fast:
        for index, argument in pending:
            record = _run_one(argument)
            records_by_index[index] = record
            _write_record(record, argument[0], output_dir, fingerprint)
            completed_count += 1
            if progress is not None:
                progress(completed_count, len(paths), record)
            if fail_fast and record.status == "error":
                break
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            completed = executor.map(_run_one, (argument for _, argument in pending))
            for (index, argument), record in zip(pending, completed):
                records_by_index[index] = record
                _write_record(record, argument[0], output_dir, fingerprint)
                completed_count += 1
                if progress is not None:
                    progress(completed_count, len(paths), record)

    records = [records_by_index[index] for index in sorted(records_by_index)]

    operation_name = normalized[0] if len(normalized) == 1 else "multiple"
    manifest = BatchManifest(
        operation=operation_name,
        records=tuple(records),
        analyses=normalized,
        configuration_fingerprint=fingerprint,
        unsupported_inputs=tuple(str(path) for path in discovery.unsupported),
    )
    payload = {
        "analyses": list(normalized),
        "configuration_fingerprint": fingerprint,
        "operation": operation_name,
        "records": [_record_payload(record) for record in records],
        "schema_version": BATCH_SCHEMA_VERSION,
        "unsupported_inputs": list(manifest.unsupported_inputs),
    }
    _atomic_write_json(output_dir / "batch-manifest.json", payload)
    _write_csv_index(records, output_dir)
    return manifest
