#!/usr/bin/env python3
"""Run the permanent openWFN numerical validation registry."""

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from openwfn.analysis.basis import ao_atom_indices, overlap_matrix
from openwfn.analysis.orbitals import frontier_orbitals
from openwfn.analysis.population import mulliken_population
from openwfn.parsers.gaussian.fchk import parse_fchk


def observations(path: Path) -> dict[str, float]:
    data = parse_fchk(path)
    values = {"energy_hartree": float(data.molecule.metadata.energy_hartree)}
    if data.alpha_orbitals is not None:
        values["gap_ev"] = frontier_orbitals(data.alpha_orbitals).gap_ev
    if data.basis is not None and data.total_density is not None:
        overlap = overlap_matrix(data.basis, data.molecule)
        result = mulliken_population(
            data.molecule, data.total_density, overlap, ao_atom_indices(data.basis)
        )
        values["electron_count"] = result.electron_count
    return values


def run(manifest_path: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results: list[dict[str, object]] = []
    failed = False
    for case in manifest["cases"]:
        if case["status"] == "pending":
            results.append({"case": case["id"], "status": "pending", "reason": case["reason"]})
            continue
        source = ROOT / case["path"]
        digest = sha256(source.read_bytes()).hexdigest()
        if digest != case["sha256"]:
            failed = True
            results.append({"case": case["id"], "status": "failed", "error": "SHA-256 mismatch"})
            continue
        observed = observations(source)
        for target in case["targets"]:
            metric = target["metric"]
            expected = float(target["expected"])
            actual = float(observed[metric])
            absolute_error = abs(actual - expected)
            relative_error = absolute_error / abs(expected) if expected else absolute_error
            status = "passed" if absolute_error <= float(target["absolute_tolerance"]) else "failed"
            failed |= status == "failed"
            results.append({
                "case": case["id"], "metric": metric, "expected": expected,
                "observed": actual, "absolute_error": absolute_error,
                "relative_error": relative_error,
                "tolerance": float(target["absolute_tolerance"]), "status": status,
            })
    return {"schema_version": "1.0", "status": "failed" if failed else "passed", "results": results}


def markdown(payload: dict[str, object]) -> str:
    lines = ["# openWFN Scientific Validation Report", "", f"Overall status: **{str(payload['status']).upper()}**", "", "| Case | Metric | Expected | Observed | Absolute error | Tolerance | Status |", "|---|---|---:|---:|---:|---:|---|"]
    for item in payload["results"]:
        if item["status"] == "pending":
            lines.append(f"| {item['case']} | pending | — | — | — | — | Pending |")
        elif "error" in item:
            lines.append(f"| {item['case']} | checksum | — | — | — | — | Failed |")
        else:
            lines.append(
                f"| {item['case']} | {item['metric']} | {item['expected']:.12g} | "
                f"{item['observed']:.12g} | {item['absolute_error']:.3g} | "
                f"{item['tolerance']:.3g} | {str(item['status']).title()} |"
            )
    lines.extend(("", "Pending cases require provenance-complete, redistribution-safe reference inputs; they are not counted as passes.", ""))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "validation" / "manifest.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "validation")
    args = parser.parse_args()
    payload = run(args.manifest)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "results.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "report.md").write_text(markdown(payload), encoding="utf-8")
    return 0 if payload["status"] == "passed" else 5


if __name__ == "__main__":
    raise SystemExit(main())
