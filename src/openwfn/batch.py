"""Deterministic multi-input analysis runner."""

import csv
import io
import json
from concurrent.futures import FIRST_COMPLETED, Executor, Future, ProcessPoolExecutor, wait
from dataclasses import dataclass, field, replace
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Callable, Iterator, Literal, cast

from . import __version__
from .analysis.registry import _resolve, available_analyses, run_analysis_safe
from .api import load
from .data import INTEROP_SCHEMA_VERSION
from .formats import iodata_format_ids, path_matches_declared_format
from .model import MODEL_SCHEMA_VERSION
from .parsers.registry import DEFAULT_REGISTRY
from .results import RESULT_SCHEMA_VERSION, ResultRecord

BATCH_SCHEMA_VERSION = "1.0"
BATCH_IMPLEMENTATION_TOKEN = "0.9-workflow-hardening-1"
ProgressCallback = Callable[[int, int, "BatchRecord"], None]
FrontierSpin = Literal["alpha", "beta", "all"]


@dataclass(frozen=True, slots=True)
class UnsupportedInput:
    path: str
    reason: str
    sha256: str | None


@dataclass(frozen=True, slots=True)
class InputDiscovery:
    inputs: tuple[Path, ...]
    unsupported: tuple[Path, ...] = ()
    unsupported_details: tuple[UnsupportedInput, ...] = ()


@dataclass(frozen=True, slots=True)
class BatchRecord:
    input_path: str
    status: Literal["success", "partial", "error"]
    result: dict[str, object] | None = None
    error: str | None = None
    input_sha256: str | None = None
    results: tuple[ResultRecord, ...] = ()
    skipped: bool = False
    source_format: str | None = None


@dataclass(frozen=True, slots=True)
class BatchManifest:
    operation: str
    records: tuple[BatchRecord, ...]
    analyses: tuple[str, ...] = ()
    configuration_fingerprint: str = ""
    unsupported_inputs: tuple[str, ...] = ()
    unsupported_details: tuple[UnsupportedInput, ...] = ()
    attempted_count: int = 0
    stopped_early: bool = False
    status: Literal["success", "partial", "failed"] = "success"
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
    format_hint: str | None = None,
    format_hints: dict[Path, str] | None = None,
) -> InputDiscovery:
    """Expand files and directories into supported, deduplicated inputs."""

    supported_suffixes = set(DEFAULT_REGISTRY.supported_suffixes())
    hinted_paths = {key.resolve() for key in (format_hints or {})}
    discovered: list[Path] = []
    unsupported: list[Path] = []
    seen: set[Path] = set()
    unsupported_seen: set[Path] = set()

    def add(path: Path) -> None:
        identity = path.resolve()
        if identity in seen or identity in unsupported_seen or _inside(path, output_dir):
            return
        if (
            format_hint is not None
            or identity in hinted_paths
            or path.suffix.lower() in supported_suffixes
            or path_matches_declared_format(path)
        ):
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
    return InputDiscovery(
        tuple(discovered), tuple(unsupported),
        tuple(
            UnsupportedInput(
                path=str(path),
                reason="No registered filename pattern matches; provide an explicit format hint if this is a supported input.",
                sha256=_file_sha256(path),
            )
            for path in unsupported
        ),
    )


def _file_sha256(path: Path) -> str | None:
    try:
        digest = sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _backend_version() -> str | None:
    try:
        return version("qc-iodata")
    except PackageNotFoundError:
        return None


def _configuration_fingerprint(
    analyses: tuple[str, ...],
    frontier_spin: FrontierSpin = "alpha",
    *,
    format_hint: str | None = None,
    format_hints: dict[Path, str] | None = None,
) -> str:
    payload = json.dumps(
        {
            "analyses": list(analyses),
            "analysis_versions": {name: _resolve(name).version for name in analyses},
            "frontier_spin": frontier_spin,
            "openwfn_version": __version__,
            "implementation_token": BATCH_IMPLEMENTATION_TOKEN,
            "batch_schema_version": BATCH_SCHEMA_VERSION,
            "result_schema_version": RESULT_SCHEMA_VERSION,
            "model_schema_version": MODEL_SCHEMA_VERSION,
            "interop_schema_version": INTEROP_SCHEMA_VERSION,
            "backend_version": _backend_version(),
            "format_hint": format_hint,
            "format_hints": {
                str(path): hint for path, hint in sorted(
                    (format_hints or {}).items(), key=lambda item: str(item[0])
                )
            },
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


def _run_one(
    arguments: tuple[Path, tuple[str, ...]] | tuple[Path, tuple[str, ...], str | None],
) -> BatchRecord:
    path, analyses = arguments[:2]
    format_hint = arguments[2] if len(arguments) == 3 else None
    try:
        calculation = load(path, format_hint=format_hint)
        results = tuple(run_analysis_safe(calculation.data, name) for name in analyses)
        usable = [result for result in results if result.status in {"success", "partial"}]
        if results and all(result.status == "success" for result in results):
            status = "success"
        elif usable:
            status = "partial"
        else:
            status = "error"
        provenance = calculation.data.provenance
        checksum = provenance.sha256 if provenance else _file_sha256(path)
        errors = [result.error.message for result in results if result.error]
        return BatchRecord(
            input_path=str(path),
            status=status,
            result=usable[0].data if usable else None,
            error="; ".join(errors) if status == "error" else None,
            input_sha256=checksum,
            results=results,
            source_format=provenance.source_format if provenance else format_hint,
        )
    except Exception as exc:
        return BatchRecord(
            str(path),
            "error",
            error=str(exc),
            input_sha256=_file_sha256(path),
            source_format=format_hint,
        )


def _run_parallel(
    pending: list[tuple[int, tuple[Path, tuple[str, ...]] | tuple[Path, tuple[str, ...], str | None]]],
    workers: int,
    *,
    runner: Callable[[tuple[Path, tuple[str, ...]] | tuple[Path, tuple[str, ...], str | None]], BatchRecord] = _run_one,
    executor_factory: type[Executor] = ProcessPoolExecutor,
) -> Iterator[tuple[int, Path, BatchRecord]]:
    remaining = iter(pending)
    with executor_factory(max_workers=workers) as executor:
        futures: dict[
            Future[BatchRecord],
            tuple[int, tuple[Path, tuple[str, ...]] | tuple[Path, tuple[str, ...], str | None]],
        ] = {}

        def submit_next() -> bool:
            try:
                index, argument = next(remaining)
            except StopIteration:
                return False
            futures[executor.submit(runner, argument)] = (index, argument)
            return True

        for _ in range(min(len(pending), workers * 2)):
            submit_next()
        while futures:
            done, _ = wait(futures, return_when=FIRST_COMPLETED)
            for future in done:
                index, argument = futures.pop(future)
                yield index, argument[0], future.result()
                submit_next()


def _record_payload(record: BatchRecord) -> dict[str, object]:
    return {
        "error": record.error,
        "input_path": record.input_path,
        "input_sha256": record.input_sha256,
        "result": record.result,
        "results": [result.as_dict() for result in record.results],
        "skipped": record.skipped,
        "source_format": record.source_format,
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
        source_format=payload.get("source_format"),
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
    frontier_spin: FrontierSpin = "alpha",
    format_hint: str | None = None,
    format_hints: dict[Path, str] | None = None,
) -> BatchManifest:
    if workers < 1:
        raise ValueError("workers must be at least one")
    if frontier_spin not in {"alpha", "beta", "all"}:
        raise ValueError("frontier spin must be 'alpha', 'beta', or 'all'")
    requested = analyses if analyses is not None else ((operation or "summary"),)
    normalized_requested = tuple(
        dict.fromkeys(name.strip().lower() for name in requested if name.strip())
    )
    if not normalized_requested:
        raise ValueError("at least one analysis is required")
    frontier_analysis = {
        "alpha": "frontier",
        "beta": "beta-frontier",
        "all": "frontier-all",
    }[frontier_spin]
    normalized = tuple(
        frontier_analysis if name == "frontier" else name for name in normalized_requested
    )
    supported = available_analyses()
    unknown = tuple(name for name in normalized if name not in supported)
    if unknown:
        raise ValueError(
            f"Unknown batch analyses: {', '.join(unknown)}. Available analyses: "
            f"{', '.join(supported)}"
        )
    known_formats = set(iodata_format_ids())
    global_hint = format_hint.strip().lower() if format_hint is not None else None
    if global_hint is not None and global_hint not in known_formats:
        raise ValueError(f"Unknown input format hint '{format_hint}'.")
    resolved_hints: dict[Path, str] = {}
    for key, value in (format_hints or {}).items():
        identity = Path(key).resolve()
        normalized_hint = value.strip().lower()
        if normalized_hint not in known_formats:
            raise ValueError(f"Unknown input format hint '{value}' for {key}.")
        if global_hint is not None and normalized_hint != global_hint:
            raise ValueError(f"Format map conflict for {key}: {normalized_hint} != {global_hint}.")
        if identity in resolved_hints and resolved_hints[identity] != normalized_hint:
            raise ValueError(f"Format map conflict for resolved path {identity}.")
        resolved_hints[identity] = normalized_hint
    discovery = discover_inputs(
        inputs, recursive=recursive, output_dir=output_dir,
        format_hint=global_hint, format_hints=resolved_hints,
    )
    paths = list(discovery.inputs)
    unknown_paths = resolved_hints.keys() - {path.resolve() for path in paths}
    if unknown_paths:
        raise ValueError(
            "Format map path is not among discovered input files: "
            + ", ".join(str(path) for path in sorted(unknown_paths))
        )
    if not paths and not discovery.unsupported:
        raise ValueError("no input files were discovered")
    fingerprint = _configuration_fingerprint(
        normalized, frontier_spin,
        format_hint=global_hint, format_hints=resolved_hints,
    )
    records_by_index: dict[int, BatchRecord] = {}
    pending: list[tuple[int, tuple[Path, tuple[str, ...], str | None]]] = []
    completed_count = 0

    def accept(index: int, path: Path, record: BatchRecord, *, write: bool) -> None:
        nonlocal completed_count
        records_by_index[index] = record
        if write:
            _write_record(record, path, output_dir, fingerprint)
        completed_count += 1
        if progress is not None:
            progress(completed_count, len(paths), record)

    if fail_fast:
        for index, path in enumerate(paths):
            cached = (
                _load_completed_record(path, output_dir, _file_sha256(path), fingerprint)
                if resume else None
            )
            if cached is not None:
                accept(index, path, cached, write=False)
                continue
            argument = (path, normalized, resolved_hints.get(path.resolve(), global_hint))
            record = _run_one(argument)
            accept(index, path, record, write=True)
            if record.status == "error":
                break
    else:
        for index, path in enumerate(paths):
            cached = (
                _load_completed_record(path, output_dir, _file_sha256(path), fingerprint)
                if resume else None
            )
            if cached is not None:
                accept(index, path, cached, write=False)
            else:
                pending.append((index, (path, normalized, resolved_hints.get(path.resolve(), global_hint))))

    if not fail_fast and workers == 1:
        for index, argument in pending:
            record = _run_one(argument)
            accept(index, argument[0], record, write=True)
    elif not fail_fast:
        for index, path, record in _run_parallel(pending, workers):
            accept(index, path, record, write=True)

    records = [records_by_index[index] for index in sorted(records_by_index)]
    stopped_early = bool(fail_fast and len(records) < len(paths))
    if discovery.unsupported or any(record.status == "error" for record in records):
        aggregate_status: Literal["success", "partial", "failed"] = "failed"
    elif any(record.status == "partial" for record in records):
        aggregate_status = "partial"
    else:
        aggregate_status = "success"

    operation_name = normalized[0] if len(normalized) == 1 else "multiple"
    manifest = BatchManifest(
        operation=operation_name,
        records=tuple(records),
        analyses=normalized,
        configuration_fingerprint=fingerprint,
        unsupported_inputs=tuple(str(path) for path in discovery.unsupported),
        unsupported_details=discovery.unsupported_details,
        attempted_count=len(records),
        stopped_early=stopped_early,
        status=aggregate_status,
    )
    payload = {
        "analyses": list(normalized),
        "configuration_fingerprint": fingerprint,
        "operation": operation_name,
        "records": [_record_payload(record) for record in records],
        "schema_version": BATCH_SCHEMA_VERSION,
        "openwfn_version": __version__,
        "implementation_token": BATCH_IMPLEMENTATION_TOKEN,
        "model_schema_version": MODEL_SCHEMA_VERSION,
        "interop_schema_version": INTEROP_SCHEMA_VERSION,
        "result_schema_version": RESULT_SCHEMA_VERSION,
        "backend_version": _backend_version(),
        "analysis_versions": {name: _resolve(name).version for name in normalized},
        "unsupported_inputs": list(manifest.unsupported_inputs),
        "unsupported_details": [
            {"path": item.path, "reason": item.reason, "sha256": item.sha256}
            for item in manifest.unsupported_details
        ],
        "attempted_count": manifest.attempted_count,
        "stopped_early": manifest.stopped_early,
        "status": manifest.status,
    }
    _atomic_write_json(output_dir / "batch-manifest.json", payload)
    _write_csv_index(records, output_dir)
    return manifest
