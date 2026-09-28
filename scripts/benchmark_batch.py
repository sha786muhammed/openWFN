"""Run a deterministic openWFN batch-throughput benchmark."""

from __future__ import annotations

import argparse
import json
import platform
import tempfile
import time
import tracemalloc
from pathlib import Path

from openwfn import __version__
from openwfn.batch import run_batch


def positive_integer(value: str) -> int:
    """Parse a command-line value that must be greater than zero."""
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return parsed


def stage_inputs(directory: Path, count: int) -> list[Path]:
    """Write a deterministic collection of supported structure inputs."""
    directory.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    contents = "3\nwater benchmark\nO 0 0 0\nH 0 0 1\nH 1 0 0\n"
    for index in range(count):
        path = directory / f"water-{index:06d}.xyz"
        path.write_text(contents, encoding="utf-8")
        paths.append(path)
    return paths


def run_benchmark(count: int, workers: int, workspace: Path) -> dict[str, object]:
    """Run the real summary batch path and return machine-readable evidence."""
    inputs = stage_inputs(workspace / "inputs", count)
    tracemalloc.start()
    started = time.perf_counter()
    try:
        manifest = run_batch(inputs, "summary", workers, workspace / "results")
        elapsed = time.perf_counter() - started
        _, peak_memory = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    successes = sum(record.status == "success" for record in manifest.records)
    partial = sum(record.status == "partial" for record in manifest.records)
    failures = sum(record.status == "error" for record in manifest.records)
    return {
        "elapsed_seconds": elapsed,
        "failures": failures,
        "files_per_second": count / elapsed,
        "input_count": count,
        "openwfn_version": __version__,
        "partial": partial,
        "peak_python_memory_bytes": peak_memory,
        "python_version": platform.python_version(),
        "successes": successes,
        "workers": workers,
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=positive_integer, default=1000)
    parser.add_argument("--workers", type=positive_integer, default=1)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.workspace is not None:
        evidence = run_benchmark(args.count, args.workers, args.workspace)
    else:
        with tempfile.TemporaryDirectory(prefix="openwfn-benchmark-") as temporary:
            evidence = run_benchmark(args.count, args.workers, Path(temporary))

    _write_json(args.output, evidence)
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
