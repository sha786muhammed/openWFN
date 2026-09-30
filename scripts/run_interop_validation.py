#!/usr/bin/env python3
"""Validate every advertised interoperability format against pinned fixtures."""

from __future__ import annotations

import json
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from openwfn.analysis.basis import ao_atom_indices  # noqa: E402
from openwfn.analysis.registry import run_analysis_safe  # noqa: E402
from openwfn.capabilities import infer_capabilities  # noqa: E402
from openwfn.formats import iodata_format_ids  # noqa: E402
from openwfn.ingest import load_input  # noqa: E402
from openwfn.services import density_integration  # noqa: E402


def _component_states(data: Any) -> set[str]:
    present = {
        name
        for name in ("structure", "calculation", "periodic", "integrals")
        if getattr(data, name) is not None
    }
    if data.grids:
        present.add("grids")
    if any(
        value is not None
        for value in (
            data.metadata.source_program,
            data.metadata.source_program_version,
            data.metadata.title,
            data.metadata.energy_hartree,
        )
    ):
        present.add("metadata")
    return present


def _validate_entry(entry: dict[str, Any]) -> dict[str, Any]:
    format_id = str(entry["format_id"])
    errors: list[str] = []
    source = ROOT / str(entry["path"])
    if not source.is_file():
        return {"format_id": format_id, "status": "FAILED", "errors": ["fixture is missing"]}
    digest = sha256(source.read_bytes()).hexdigest()
    if digest != entry["sha256"]:
        errors.append("fixture SHA-256 differs from manifest")
    if not entry["provenance"].get("redistribution_safe"):
        errors.append("redistribution provenance is not approved")
    try:
        data = load_input(source, format_hint=format_id)
    except Exception as exc:
        errors.append(f"ingestion failed: {type(exc).__name__}: {exc}")
        return {"format_id": format_id, "status": "FAILED", "errors": errors}

    expected_source = entry["expected_source"]
    provenance = data.provenance
    if provenance is None or provenance.sha256 != digest:
        errors.append("normalized provenance lost source SHA-256")
    if provenance is None or provenance.source_format != expected_source["format"]:
        errors.append("normalized provenance has incorrect source format")
    if provenance is None or not provenance.parser or not provenance.parser_version:
        errors.append("normalized provenance lacks parser identity/version")
    backend = getattr(provenance, "backend", None) if provenance is not None else None
    backend_version = getattr(provenance, "backend_version", None) if provenance is not None else None
    expected_backend = expected_source["backend"]
    if expected_backend == "iodata":
        if backend != "iodata" or backend_version != expected_source["backend_version"]:
            errors.append("IOData backend identity/version differs from manifest")
    elif backend is not None:
        errors.append("native fixture unexpectedly used the optional backend")

    components = _component_states(data)
    expected_components = set(entry["expected_components"])
    if components != expected_components:
        errors.append(
            f"canonical components differ: expected {sorted(expected_components)}, got {sorted(components)}"
        )
    atom_count = entry.get("expected_atom_count")
    if atom_count is not None and (data.structure is None or len(data.structure.coordinates) != atom_count):
        errors.append(f"normalized atom count differs from {atom_count}")
    for name, expected in entry["expected_capabilities"].items():
        capability = infer_capabilities(data).get(name)
        observed = capability.state if capability is not None else None
        if observed != expected:
            errors.append(f"capability {name}: expected {expected}, got {observed}")

    analyses = entry["expected_analyses"]
    for name in analyses["available"]:
        result = run_analysis_safe(data, name)
        if result.status != "success":
            errors.append(
                f"analysis {name}: expected success, got {result.status}/{result.validation_status}"
            )
    for name in analyses.get("partial", []):
        result = run_analysis_safe(data, name)
        if result.status != "partial":
            errors.append(
                f"analysis {name}: expected partial, got {result.status}/{result.validation_status}"
            )
    for name in analyses["unsupported"]:
        result = run_analysis_safe(data, name)
        if result.status != "failed" or result.validation_status != "Unsupported":
            errors.append(
                f"analysis {name}: expected structured Unsupported, got {result.status}/{result.validation_status}"
            )

    return {"format_id": format_id, "status": "PASSED" if not errors else "FAILED", "errors": errors}


def _observation(data: Any, name: str, grid: dict[str, float]) -> Any:
    if name == "atomic_numbers":
        return list(data.structure.atomic_numbers)
    if name == "coordinates_angstrom":
        return [list(row) for row in data.structure.coordinates]
    if name == "energy_hartree":
        return data.metadata.energy_hartree
    calc = data.calculation
    if calc is None:
        raise ValueError(f"{name} requires a complete wavefunction")
    if name == "electron_count":
        return sum(calc.alpha_orbitals.occupations) + (
            sum(calc.beta_orbitals.occupations) if calc.beta_orbitals else 0
        )
    if name == "basis_functions":
        return calc.basis.n_functions
    if name == "ao_atom_indices":
        return list(ao_atom_indices(calc.basis))
    if name == "alpha_energies_hartree":
        return list(calc.alpha_orbitals.energies)
    if name == "alpha_occupations":
        return list(calc.alpha_orbitals.occupations)
    if name == "frontier_gap_hartree":
        result = run_analysis_safe(data, "frontier")
        if result.status != "success":
            raise ValueError("frontier analysis did not succeed")
        return result.data["gap_hartree"]
    if name == "mulliken_charges":
        result = run_analysis_safe(data, "mulliken")
        if result.status != "success":
            raise ValueError("Mulliken analysis did not succeed")
        return result.data["atomic_charges"]
    if name == "density_integral_electrons":
        result = density_integration(calc, "total", grid["spacing_bohr"], grid["padding_bohr"])
        return result.data["electron_count"]
    raise ValueError(f"unknown validation metric: {name}")


def _absolute_error(expected: Any, observed: Any) -> float:
    if isinstance(expected, list):
        if not isinstance(observed, (list, tuple)) or len(expected) != len(observed):
            raise ValueError("reference and observation have different shapes")
        return max((_absolute_error(left, right) for left, right in zip(expected, observed)), default=0.0)
    if observed is None:
        raise ValueError("reference value is unavailable")
    return abs(float(expected) - float(observed))


def run_cross_format_validation(manifest_path: Path) -> dict[str, object]:
    """Compare pinned fixtures to explicit numerical references."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    results: list[dict[str, object]] = []
    for group in ("equivalent_water", "program_references"):
        for case in manifest[group]:
            source = ROOT / case["path"]
            try:
                if sha256(source.read_bytes()).hexdigest() != case["sha256"]:
                    raise ValueError("fixture SHA-256 differs from cross-format manifest")
                data = load_input(source, format_hint=case["format_id"])
                for metric in case["metrics"]:
                    observed = _observation(data, metric["name"], manifest["density_grid"])
                    if metric["name"] in {"alpha_energies_hartree", "alpha_occupations"}:
                        observed = observed[:len(metric["expected"])]
                    error = _absolute_error(metric["expected"], observed)
                    tolerance = float(metric["absolute_tolerance"])
                    results.append({
                        "group": group, "format_id": case["format_id"], "metric": metric["name"],
                        "expected": metric["expected"], "observed": observed,
                        "absolute_error": error, "tolerance": tolerance,
                        "status": "PASSED" if error <= tolerance else "FAILED",
                    })
            except Exception as exc:
                results.append({"group": group, "format_id": case["format_id"],
                                "metric": "ingestion", "status": "FAILED",
                                "error": f"{type(exc).__name__}: {exc}"})
    failed = sum(item["status"] == "FAILED" for item in results)
    return {"status": "PASSED" if failed == 0 else "FAILED",
            "reference_note": manifest["reference_note"], "passed": len(results) - failed,
            "failed": failed, "total": len(results), "results": results}


def run(
    manifest_path: Path, *, output_dir: Path | None = None,
    cross_manifest_path: Path | None = None,
) -> dict[str, object]:
    """Run the deterministic 25-format contract and write machine/human reports."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    entries = manifest["formats"]
    ids = [entry["format_id"] for entry in entries]
    if len(ids) != len(set(ids)) or tuple(sorted(ids)) != iodata_format_ids():
        raise ValueError("Manifest does not contain the exact pinned 25-format inventory")
    results = [_validate_entry(entry) for entry in entries]
    passed = sum(item["status"] == "PASSED" for item in results)
    cross_path = cross_manifest_path or ROOT / "validation/interop/cross_format_manifest.json"
    cross = run_cross_format_validation(cross_path)
    report: dict[str, object] = {
        "schema_version": "1.0",
        "overall": "PASSED" if passed == len(results) and cross["status"] == "PASSED" else "FAILED",
        "passed": passed,
        "failed": len(results) - passed,
        "total": len(results),
        "formats": results,
        "cross_format": cross,
    }
    output = Path(output_dir) if output_dir is not None else ROOT / "validation" / "interop"
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# openWFN interoperability format validation",
        "",
        f"Overall: **{report['overall']}** ({passed}/{len(results)} formats)",
        "",
        "| Format | Status |", "|---|---|",
    ]
    lines.extend(f"| `{item['format_id']}` | {item['status']} |" for item in results)
    for item in results:
        if item["errors"]:
            lines.extend(["", f"## {item['format_id']}", ""])
            lines.extend(f"- {error}" for error in item["errors"])
    lines.extend(["", "## Cross-format scientific equivalence", "",
                  f"Status: **{cross['status']}** ({cross['passed']}/{cross['total']} metrics)", "",
                  str(cross["reference_note"]), "",
                  "| Format | Metric | Expected | Observed | Absolute error | Tolerance | Status |",
                  "|---|---|---|---|---:|---:|---|"])
    for item in cross["results"]:
        if "error" in item:
            lines.append(f"| `{item['format_id']}` | {item['metric']} | — | {item['error']} | — | — | FAILED |")
        else:
            lines.append(
                f"| `{item['format_id']}` | {item['metric']} | {item['expected']} | "
                f"{item['observed']} | {item['absolute_error']:.3g} | "
                f"{item['tolerance']:.3g} | {item['status']} |"
            )
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run(ROOT / "validation" / "interop" / "manifest.json")
    print(f"{result['overall']}: {result['passed']}/{result['total']} formats")
    raise SystemExit(0 if result["overall"] == "PASSED" else 1)
