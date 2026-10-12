"""Compare streamed integration with a materialized grid in fresh processes."""
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path


def measure(path: Path, spacing: float, padding: float, mode: str) -> dict:
    from openwfn import load
    from openwfn.analysis.density import integrate_density
    from openwfn.scientific import expected_electron_count
    from openwfn.services import density_grid, density_integration

    started = time.perf_counter()
    calculation = load(path).data.calculation
    if calculation is None:
        raise ValueError("Benchmark input requires a molecular wavefunction")
    if mode == "streaming":
        result = density_integration(calculation, "total", spacing, padding)
        count = result.data["electron_count"]
        status = result.status
    else:
        result = integrate_density(density_grid(calculation, "total", spacing, padding),
            expected_electron_count(calculation, "total").value)
        count = result.electron_count
        status = "success" if result.passed else "partial"
    elapsed = time.perf_counter() - started
    try:
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        peak_bytes = peak if sys.platform == "darwin" else peak * 1024
    except ImportError:
        peak_bytes = None
    return {"input": str(path), "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "mode": mode, "elapsed_seconds": elapsed, "peak_rss_bytes": peak_bytes,
        "electron_count": count, "status": status}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="+", type=Path, default=[
        root / "examples/water/water.fchk",
        root / "examples/everyday-qc/ethanol.molden",
        root / "examples/research-workflows/biphenyl/biphenyl.molden"])
    parser.add_argument("--spacing", type=float, default=.2)
    parser.add_argument("--padding", type=float, default=5.)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker", choices=("streaming", "materialized"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(measure(args.inputs[0], args.spacing, args.padding, args.worker)))
        return 0
    if args.output is None:
        parser.error("--output is required")
    if args.output.exists():
        parser.error("Output already exists; choose a new report filename")
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    records = []
    for path in args.inputs:
        for mode in ("materialized", "streaming"):
            command = [sys.executable, str(Path(__file__).resolve()), "--worker", mode,
                "--inputs", str(path.resolve()), "--spacing", str(args.spacing),
                "--padding", str(args.padding)]
            records.append(json.loads(subprocess.check_output(command, text=True, env=env, timeout=120)))
    report = {"python": platform.python_version(), "platform": platform.platform(),
        "spacing_bohr": args.spacing, "padding_bohr": args.padding, "threads": 1,
        "records": records, "limitations": [
            "Peak RSS includes interpreter, input loading and native-library allocations.",
            "Windows peak RSS is unavailable in this dependency-free benchmark.",
            "Runtime and memory vary between runs; these are not hard resource quotas.",
            "Same-engine agreement is not independent scientific validation.",
            "This benchmark writes no cubes or HTML; only the JSON report is saved."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(f"Saved {len(records)} measurements to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
