#!/usr/bin/env python3
"""Compare openWFN observations with independently generated references."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Sequence
from hashlib import sha256
from pathlib import Path
from typing import TypeAlias

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from openwfn.analysis.basis import ao_atom_indices, overlap_matrix
from openwfn.analysis.orbitals import frontier_orbitals
from openwfn.analysis.population import lowdin_population, mulliken_population
from openwfn.parsers.gaussian.fchk import parse_fchk
from openwfn.services import density_integration
from openwfn.validation.convergence import GridPoint, assess_convergence

MetricValue: TypeAlias = float | list[float]


def _values(value: MetricValue | tuple[float, ...]) -> list[float]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        result = [float(item) for item in value]
    else:
        result = [float(value)]
    if not result or not all(math.isfinite(item) for item in result):
        raise ValueError("benchmark values must be finite and nonempty")
    return result


def compare_metric(
    expected: MetricValue,
    observed: MetricValue | tuple[float, ...],
    tolerance: float,
) -> tuple[float, str]:
    """Return maximum absolute error and pass/fail status."""

    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("benchmark tolerance must be finite and non-negative")
    expected_values = _values(expected)
    observed_values = _values(observed)
    if len(expected_values) != len(observed_values):
        raise ValueError("benchmark vector length mismatch")
    error = max(abs(reference - actual) for reference, actual in zip(
        expected_values, observed_values, strict=True
    ))
    return error, "passed" if error <= tolerance else "failed"


def observations(path: Path) -> dict[str, MetricValue | tuple[float, ...]]:
    """Calculate normalized benchmark observations for one FCHK input."""

    data = parse_fchk(path)
    values: dict[str, MetricValue | tuple[float, ...]] = {}
    energy = data.molecule.metadata.energy_hartree
    if energy is not None:
        values["energy_hartree"] = float(energy)
    if data.alpha_orbitals is not None:
        frontier = frontier_orbitals(data.alpha_orbitals)
        values.update(
            {
                "homo_hartree": frontier.homo_hartree,
                "lumo_hartree": frontier.lumo_hartree,
                "gap_hartree": frontier.gap_hartree,
                "gap_ev": frontier.gap_ev,
            }
        )
    if data.basis is not None and data.total_density is not None:
        overlap = overlap_matrix(data.basis, data.molecule)
        mapping = ao_atom_indices(data.basis)
        mulliken = mulliken_population(data.molecule, data.total_density, overlap, mapping)
        lowdin = lowdin_population(data.molecule, data.total_density, overlap, mapping)
        values.update(
            {
                "mulliken_electron_count": mulliken.electron_count,
                "mulliken_atomic_charges": mulliken.atomic_charges,
                "lowdin_electron_count": lowdin.electron_count,
                "lowdin_atomic_charges": lowdin.atomic_charges,
            }
        )
    return values


def _source_path(case: dict[str, object], input_root: Path | None) -> Path:
    raw = Path(str(case["input"]))
    if raw.is_absolute():
        return raw
    return (input_root or ROOT) / raw


def _grid_convergence(source: Path, metric: dict[str, object]) -> dict[str, object]:
    data = parse_fchk(source)
    density_kind = str(metric["density_kind"])
    padding = float(metric["padding"])
    spacings = sorted((float(value) for value in metric["spacings"]), reverse=True)
    points: list[GridPoint] = []
    for spacing in spacings:
        record = density_integration(data, density_kind, spacing, padding)
        points.append(
            GridPoint(
                spacing=spacing,
                padding=padding,
                electron_count=float(record.data["electron_count"]),
                expected_electrons=float(record.data["expected_electrons"]),
            )
        )
    decision = assess_convergence(
        points,
        maximum_relative_error=float(metric["maximum_relative_error"]),
        maximum_successive_change=float(metric["maximum_successive_change"]),
    )
    return {
        "metric": str(metric["name"]),
        "unit": str(metric["unit"]),
        "density_kind": density_kind,
        "points": [
            {
                "spacing": point.spacing,
                "padding": point.padding,
                "electron_count": point.electron_count,
                "expected_electrons": point.expected_electrons,
            }
            for point in points
        ],
        "relative_error": decision.relative_error,
        "successive_change": decision.successive_change,
        "maximum_relative_error": float(metric["maximum_relative_error"]),
        "maximum_successive_change": float(metric["maximum_successive_change"]),
        "message": decision.message,
        "status": decision.status,
    }


def run(manifest_path: Path, input_root: Path | None = None) -> dict[str, object]:
    """Run all active cases and preserve pending cases in manifest order."""

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results: list[dict[str, object]] = []
    counts = {"passed": 0, "failed": 0, "pending": 0}
    for case in manifest["cases"]:
        case_id = str(case["id"])
        if case["status"] == "pending":
            counts["pending"] += 1
            results.append(
                {"case": case_id, "status": "pending", "reason": str(case["reason"])}
            )
            continue

        source = _source_path(case, input_root)
        try:
            digest = sha256(source.read_bytes()).hexdigest()
            if digest != case["sha256"]:
                raise ValueError("SHA-256 mismatch")
            observed = observations(source)
            for metric in case["metrics"]:
                if metric.get("kind") == "grid_convergence":
                    item = {"case": case_id, **_grid_convergence(source, metric)}
                    counts[str(item["status"])] += 1
                    results.append(item)
                    continue
                name = str(metric["name"])
                if name not in observed:
                    raise ValueError(f"Unsupported benchmark metric or unavailable data: {name}")
                tolerance = float(
                    metric.get("absolute_tolerance", metric.get("max_absolute_tolerance"))
                )
                error, status = compare_metric(
                    metric["expected"], observed[name], tolerance
                )
                counts[status] += 1
                results.append(
                    {
                        "case": case_id,
                        "metric": name,
                        "unit": str(metric["unit"]),
                        "expected": metric["expected"],
                        "observed": observed[name],
                        "absolute_error": error,
                        "tolerance": tolerance,
                        "status": status,
                    }
                )
        except (KeyError, OSError, TypeError, ValueError) as exc:
            counts["failed"] += 1
            results.append({"case": case_id, "status": "failed", "error": str(exc)})

    if counts["failed"]:
        status = "failed"
    elif counts["pending"]:
        status = "pending"
    else:
        status = "passed"
    return {
        "schema_version": "1.0",
        "status": status,
        "summary": counts,
        "results": results,
    }


def markdown(payload: dict[str, object]) -> str:
    lines = [
        "# openWFN Independent Benchmark Report",
        "",
        f"Overall status: **{str(payload['status']).upper()}**",
        "",
        "| Case | Metric | Expected | Observed | Absolute error | Tolerance | Status |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for item in payload["results"]:
        if item["status"] == "pending":
            lines.append(f"| {item['case']} | pending | — | — | — | — | Pending |")
        elif "error" in item:
            lines.append(f"| {item['case']} | error | — | — | — | — | Failed |")
        elif "points" in item:
            lines.append(
                f"| {item['case']} | {item['metric']} | converged grid | "
                f"{item['points'][-1]['electron_count']:.12g} | "
                f"{item['relative_error']:.6g} | "
                f"{item['maximum_relative_error']:.6g} | "
                f"{str(item['status']).title()} |"
            )
        else:
            expected = json.dumps(item["expected"], separators=(",", ":"))
            observed = json.dumps(item["observed"], separators=(",", ":"))
            lines.append(
                f"| {item['case']} | {item['metric']} | {expected} | {observed} | "
                f"{item['absolute_error']:.6g} | {item['tolerance']:.6g} | "
                f"{str(item['status']).title()} |"
            )
    lines.extend(
        (
            "",
            "Pending cases are incomplete evidence and are never counted as passes.",
            "",
        )
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "validation" / "external" / "manifest.json",
    )
    parser.add_argument("--input-root", type=Path)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "validation" / "external" / "generated"
    )
    args = parser.parse_args()
    payload = run(args.manifest, args.input_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "results.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output_dir / "report.md").write_text(markdown(payload), encoding="utf-8")
    return 5 if payload["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
