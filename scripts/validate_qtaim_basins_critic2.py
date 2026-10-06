#!/usr/bin/env python3
"""Generate and verify independent Critic2 QTAIM basin reference data.

Critic2 is validation-only. This script is intentionally outside the openWFN
runtime package and never changes the production scientific engine.
"""

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Iterable

import numpy as np

from openwfn.constants import BOHR_TO_ANGSTROM
from openwfn.ingest import load_input

CRITIC2_RELEASE = "1.2"
CRITIC2_COMMIT = "9731d532c6407d35c75bbce5af449211470437a7"
DEFAULT_LEBEDEV_POINTS = 4802
REFERENCE_POPULATION_CLOSURE_TOLERANCE_E = 1.0e-2

_POSITION_HEADER = re.compile(r"Position\s*\(([^)]+)\)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class Critic2BasinRow:
    identifier: int
    name: str
    atomic_number: int
    multiplicity: int | None
    position_bohr: tuple[float, float, float]
    volume: float | None
    population: float
    laplacian_integral: float


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_fixture_sha256(path: Path, expected_sha256: str) -> str:
    actual = sha256_file(path)
    expected = expected_sha256.strip().lower()
    if actual.lower() != expected:
        raise ValueError(
            f"Fixture SHA-256 mismatch for {path}: expected {expected}, observed {actual}"
        )
    return actual


def _parse_float(token: str) -> float:
    try:
        value = float(token.replace("D", "E").replace("d", "e"))
    except ValueError as exc:
        raise ValueError(f"Critic2 table contains invalid numeric token {token!r}") from exc
    if not math.isfinite(value):
        raise ValueError("Critic2 table contains nonfinite numeric value")
    return value


def _position_factor(header_line: str) -> float:
    match = _POSITION_HEADER.search(header_line)
    if match is None:
        raise ValueError("Critic2 attractor table is missing position units")
    unit = match.group(1).strip().lower()
    if unit in {"bohr", "a.u.", "au", "atomic units", "atomic unit"}:
        return 1.0
    if unit in {"angs.", "ang.", "ang_", "angstrom", "angstroms", "å"}:
        return 1.0 / BOHR_TO_ANGSTROM
    if unit.startswith("cryst"):
        raise ValueError(
            "Critic2 crystal-coordinate attractors cannot be mapped to molecular atoms"
        )
    raise ValueError(f"Unsupported Critic2 attractor position unit: {unit}")


def _critic2_table_tokens(line: str, *, min_columns: int = 9) -> list[str] | None:
    """Return fixed table columns for a Critic2 data row, or None for non-rows."""

    tokens = line.split()
    if len(tokens) < min_columns:
        return None
    try:
        int(tokens[0])
    except ValueError:
        return None
    return tokens


def _parse_attractor_positions(
    text: str,
) -> dict[int, tuple[str, int, int | None, tuple[float, float, float]]]:
    lines = text.splitlines()
    start = None
    factor = None
    for index, line in enumerate(lines):
        if line.strip().startswith("* List of attractors integrated"):
            for header_index in range(index + 1, min(index + 8, len(lines))):
                if "Position" in lines[header_index]:
                    start = header_index + 1
                    factor = _position_factor(lines[header_index])
                    break
    if start is None or factor is None:
        raise ValueError("Critic2 output is missing the integrated-attractor table")

    rows: dict[int, tuple[str, int, int | None, tuple[float, float, float]]] = {}
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped:
            if rows:
                break
            continue
        if stripped.startswith("*"):
            break
        tokens = _critic2_table_tokens(line)
        if tokens is None:
            if rows:
                break
            continue
        identifier = int(tokens[0])
        if identifier in rows:
            raise ValueError(f"Critic2 attractor table contains duplicate id {identifier}")
        name = tokens[3]
        atomic_number = int(tokens[4])
        multiplicity = None if tokens[5] == "--" else int(tokens[5])
        coords = tuple(_parse_float(token) * factor for token in tokens[6:9])
        rows[identifier] = (name, atomic_number, multiplicity, coords)
    if not rows:
        raise ValueError("Critic2 integrated-attractor table contains no rows")
    return rows


def _parse_integrated_properties(
    text: str,
) -> dict[int, tuple[str, int, int | None, float | None, float, float]]:
    lines = text.splitlines()
    start = None
    property_names: list[str] | None = None
    for index, line in enumerate(lines):
        if line.strip().startswith("* Integrated atomic properties"):
            for header_index in range(index + 1, min(index + 12, len(lines))):
                stripped = lines[header_index].strip()
                if not stripped.startswith("# Id"):
                    continue
                header_tokens = stripped.lstrip("#").split()
                if len(header_tokens) < 7:
                    continue
                names = header_tokens[6:]
                lowered = [name.lower() for name in names]
                if "pop" in lowered and "lap" in lowered:
                    start = header_index + 1
                    property_names = names
                    break
    if start is None or property_names is None:
        marker = next(
            (index for index, line in enumerate(lines) if "Integrated atomic" in line),
            None,
        )
        if marker is None:
            excerpt_lines = lines[-40:]
        else:
            excerpt_lines = lines[max(0, marker - 4) : marker + 30]
        excerpt = "\n".join(excerpt_lines)
        raise ValueError(
            "Critic2 output is missing a Pop/Lap integrated atomic-properties table; "
            f"output excerpt follows:\n{excerpt}"
        )

    lowered_names = [name.lower() for name in property_names]
    population_index = lowered_names.index("pop")
    laplacian_index = lowered_names.index("lap")
    volume_index = lowered_names.index("volume") if "volume" in lowered_names else None

    rows: dict[int, tuple[str, int, int | None, float | None, float, float]] = {}
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("-") or stripped.startswith("Sum"):
            break
        if not stripped or stripped.startswith("#"):
            continue
        tokens = _critic2_table_tokens(line, min_columns=6 + len(property_names))
        if tokens is None:
            if rows:
                break
            continue
        expected_columns = 6 + len(property_names)
        if len(tokens) < expected_columns:
            raise ValueError(
                "Critic2 integrated-property row has fewer columns than its property header"
            )
        identifier = int(tokens[0])
        if identifier in rows:
            raise ValueError(
                f"Critic2 integrated-property table contains duplicate id {identifier}"
            )
        name = tokens[3]
        atomic_number = int(tokens[4])
        multiplicity = None if tokens[5] == "--" else int(tokens[5])
        property_tokens = tokens[6 : 6 + len(property_names)]
        volume = None if volume_index is None else _parse_float(property_tokens[volume_index])
        population = _parse_float(property_tokens[population_index])
        laplacian = _parse_float(property_tokens[laplacian_index])
        rows[identifier] = (
            name,
            atomic_number,
            multiplicity,
            volume,
            population,
            laplacian,
        )
    if not rows:
        raise ValueError("Critic2 integrated-property table contains no rows")
    return rows


def parse_critic2_basin_output(text: str) -> list[Critic2BasinRow]:
    """Parse one complete Critic2 molecular bisection integration block."""

    positions = _parse_attractor_positions(text)
    properties = _parse_integrated_properties(text)
    if set(positions) != set(properties):
        raise ValueError(
            "Critic2 attractor/property row mismatch: missing or unmatched atomic entries"
        )

    result: list[Critic2BasinRow] = []
    for identifier in sorted(positions):
        name, atomic_number, multiplicity, position_bohr = positions[identifier]
        pname, pz, pmult, volume, population, laplacian = properties[identifier]
        if (name, atomic_number, multiplicity) != (pname, pz, pmult):
            raise ValueError(
                f"Critic2 row metadata mismatch for id {identifier}: "
                f"{(name, atomic_number, multiplicity)} != {(pname, pz, pmult)}"
            )
        values = (*position_bohr, population, laplacian)
        if volume is not None:
            values = (*values, volume)
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError(f"Critic2 row {identifier} contains nonfinite values")
        result.append(
            Critic2BasinRow(
                identifier=identifier,
                name=name,
                atomic_number=atomic_number,
                multiplicity=multiplicity,
                position_bohr=position_bohr,
                volume=volume,
                population=population,
                laplacian_integral=laplacian,
            )
        )
    return result


def map_critic2_rows_to_atoms(
    rows: Iterable[Critic2BasinRow],
    atomic_numbers: np.ndarray,
    atom_positions_bohr: np.ndarray,
    *,
    tolerance_bohr: float,
) -> list[Critic2BasinRow]:
    """Map Critic2 attractors to input atoms using element and geometry."""

    if not math.isfinite(tolerance_bohr) or tolerance_bohr <= 0.0:
        raise ValueError("tolerance_bohr must be positive and finite")
    row_list = list(rows)
    numbers = np.asarray(atomic_numbers, dtype=int)
    positions = np.asarray(atom_positions_bohr, dtype=float)
    if numbers.ndim != 1 or positions.shape != (len(numbers), 3):
        raise ValueError("atom mapping inputs have incompatible shapes")
    if len(row_list) != len(numbers):
        raise ValueError(
            f"Critic2 atom mapping count mismatch: {len(row_list)} rows for {len(numbers)} atoms"
        )

    available = set(range(len(row_list)))
    ordered: list[Critic2BasinRow] = []
    for atom_index, (atomic_number, position) in enumerate(zip(numbers, positions)):
        candidates: list[tuple[float, int]] = []
        for row_index in available:
            row = row_list[row_index]
            if row.atomic_number != int(atomic_number):
                continue
            distance = float(np.linalg.norm(np.asarray(row.position_bohr) - position))
            if distance <= tolerance_bohr:
                candidates.append((distance, row_index))
        if not candidates:
            raise ValueError(
                f"Critic2 atom mapping failed for atom {atom_index} (Z={int(atomic_number)}); "
                "no attractor match lies inside the tolerance"
            )
        candidates.sort()
        if len(candidates) > 1 and abs(candidates[1][0] - candidates[0][0]) <= 1.0e-12:
            raise ValueError(
                f"Critic2 atom mapping is ambiguous for atom {atom_index}; multiple equal matches"
            )
        row_index = candidates[0][1]
        ordered.append(row_list[row_index])
        available.remove(row_index)

    if available:
        raise ValueError("Critic2 atom mapping left unmatched attractor rows")
    return ordered


def validate_reference_population_closure(
    *,
    population_sum_e: float,
    expected_electrons_e: float,
    tolerance_e: float,
    case_id: str,
) -> float:
    """Reject externally generated basin references that fail electron closure."""

    values = (population_sum_e, expected_electrons_e, tolerance_e)
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError(f"Critic2 reference electron closure inputs are nonfinite for {case_id}")
    if tolerance_e <= 0.0:
        raise ValueError("Critic2 reference electron-closure tolerance must be positive")
    residual = abs(float(population_sum_e) - float(expected_electrons_e))
    if residual > tolerance_e:
        raise ValueError(
            f"Critic2 reference electron closure failed for {case_id}: "
            f"population sum {population_sum_e:.12g} e vs expected "
            f"{expected_electrons_e:.12g} e (residual {residual:.6g} e > "
            f"{tolerance_e:.6g} e)"
        )
    return residual


def _manifest_hashes(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, str] = {}
    for case in payload.get("cases", []):
        if isinstance(case, dict) and case.get("status") == "active":
            identifier = case.get("id")
            sha256 = case.get("sha256")
            if isinstance(identifier, str) and isinstance(sha256, str):
                result[identifier] = sha256
    return result


def build_critic2_input(fchk_path: Path, *, lebedev_points: int) -> str:
    absolute = fchk_path.resolve()
    return (
        f"molecule {absolute}\n"
        f"load {absolute}\n"
        "int_radial type qags abserr 1e-10 relerr 1e-10 errprop 2 prec 1e-6\n"
        "auto\n"
        f"integrals lebedev {int(lebedev_points)}\n"
    )


def _run_critic2(
    executable: Path,
    fchk_path: Path,
    *,
    lebedev_points: int,
    critic_home: Path | None,
) -> tuple[str, str, str]:
    script = build_critic2_input(fchk_path, lebedev_points=lebedev_points)
    env = os.environ.copy()
    if critic_home is not None:
        env["CRITIC_HOME"] = str(critic_home.resolve())
    completed = subprocess.run(
        [str(executable.resolve())],
        input=script,
        text=True,
        capture_output=True,
        check=False,
        env=env,
        timeout=1800,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Critic2 failed for {fchk_path} with exit code {completed.returncode}:\n"
            f"{completed.stderr[-4000:]}"
        )
    return script, completed.stdout, completed.stderr


def _calculation_geometry(path: Path) -> tuple[np.ndarray, np.ndarray, int]:
    normalized = load_input(path)
    calculation = normalized.calculation
    if calculation is None:
        raise ValueError(f"{path} did not normalize to a molecular calculation")
    numbers = np.asarray([atom.atomic_number for atom in calculation.molecule.atoms], dtype=int)
    positions_bohr = np.asarray(
        [
            [float(value) / BOHR_TO_ANGSTROM for value in atom.coordinates]
            for atom in calculation.molecule.atoms
        ],
        dtype=float,
    )
    return numbers, positions_bohr, int(calculation.molecule.charge)


def validate_reference_populations(
    populations: list[float], *, expected_electrons: float, tolerance_e: float = 0.01
) -> dict[str, float]:
    """Reject unusable independent references; never correct their populations."""
    values = np.asarray(populations, dtype=float)
    if values.ndim != 1 or not len(values) or not np.all(np.isfinite(values)):
        raise ValueError("Independent reference populations must be finite and nonempty")
    if np.any(values < 0):
        raise ValueError("Independent reference contains negative electron populations")
    if not np.isfinite(expected_electrons) or expected_electrons <= 0:
        raise ValueError("Expected reference electron count must be positive and finite")
    if not np.isfinite(tolerance_e) or tolerance_e <= 0:
        raise ValueError("Reference closure tolerance must be positive and finite")
    residual = validate_reference_population_closure(
        population_sum_e=float(values.sum()), expected_electrons_e=expected_electrons,
        tolerance_e=tolerance_e, case_id="independent reference",
    )
    return {"expected_electrons_e": expected_electrons, "electron_count_residual_e": residual}


def assess_basin_convergence(
    *, reference_populations, medium_populations, fine_populations,
    fine_electron_residual, fine_charge_residual, fine_unresolved_electrons,
) -> dict[str, object]:
    """Apply the predeclared independent-agreement and convergence gates."""
    reference, medium, fine = (
        np.asarray(values, dtype=float)
        for values in (reference_populations, medium_populations, fine_populations)
    )
    if reference.ndim != 1 or not len(reference) or medium.shape != reference.shape or fine.shape != reference.shape:
        raise ValueError("Basin comparison requires matching nonempty atom vectors")
    if not all(np.all(np.isfinite(values)) for values in (reference, medium, fine)):
        raise ValueError("Basin comparison requires finite atom populations")
    diagnostics = np.asarray([fine_electron_residual, fine_charge_residual, fine_unresolved_electrons])
    if not np.all(np.isfinite(diagnostics)) or np.any(diagnostics < 0):
        raise ValueError("Basin comparison requires finite nonnegative diagnostics")
    reference_error = float(np.max(np.abs(fine - reference)))
    refinement_error = float(np.max(np.abs(fine - medium)))
    checks = {
        "reference_agreement": reference_error <= 0.02,
        "grid_refinement": refinement_error <= 0.01,
        "electron_closure": float(fine_electron_residual) <= 0.01,
        "charge_closure": float(fine_charge_residual) <= 0.01,
        "unresolved_electrons": float(fine_unresolved_electrons) <= 0.001,
    }
    return {
        "passed": all(checks.values()), "checks": checks,
        "max_reference_error_e": reference_error,
        "max_medium_to_fine_shift_e": refinement_error,
        "tolerances_e": {"reference_agreement": 0.02, "grid_refinement": 0.01,
                         "electron_closure": 0.01, "charge_closure": 0.01,
                         "unresolved_electrons": 0.001},
    }


def compare_openwfn_reference(reference: dict[str, object], output: Path) -> dict[str, object]:
    """Run all three prescribed grids, retaining failed scientific evidence."""
    from openwfn.analysis.atom_quadrature import AtomQuadratureSettings
    from openwfn.analysis.qtaim_basins import QTAIMBasinSettings
    from openwfn.api import load

    fixtures = reference.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError("Independent comparison requires nonempty reference fixtures")
    report = {"schema_version": 1, "passed": True, "fixtures": []}
    grids = (("coarse", 32, 8, 16, 16.), ("medium", 48, 12, 24, 18.),
             ("fine", 72, 16, 32, 20.))
    for fixture in fixtures:
        path = Path(fixture["path"])
        verify_fixture_sha256(path, fixture["sha256"])
        expected = float(sum(fixture["atomic_numbers"]) - fixture["expected_molecular_charge_e"])
        validate_reference_populations(fixture["populations_e"], expected_electrons=expected)
        calculation = load(path)
        series = {}
        for name, radial, theta, phi, extent in grids:
            settings = QTAIMBasinSettings(quadrature=AtomQuadratureSettings(
                radial_points=radial, theta_points=theta, phi_points=phi,
                radial_extent_bohr=extent, chunk_size=4096))
            started = perf_counter()
            result = calculation.qtaim_basins(settings=settings, include_boundary_diagnostics=False)
            series[name] = {"elapsed_seconds": perf_counter() - started, "result": result.as_dict()}
        medium, fine = series["medium"]["result"], series["fine"]["result"]
        if medium["status"] != "success" or fine["status"] != "success":
            assessment = {
                "passed": False,
                "reason": "Medium/fine scientific engine result is not successful; partial or failed results cannot pass validation",
            }
        else:
            diagnostics = fine["data"]["diagnostics"]
            assessment = assess_basin_convergence(
                reference_populations=fixture["populations_e"],
                medium_populations=[a["electron_population"] for a in medium["data"]["atoms"]],
                fine_populations=[a["electron_population"] for a in fine["data"]["atoms"]],
                fine_electron_residual=diagnostics["electron_count_residual"],
                fine_charge_residual=diagnostics["charge_closure_residual"],
                fine_unresolved_electrons=diagnostics["unresolved_electrons"],
            )
        report["fixtures"].append({"id": fixture["id"], "sha256": fixture["sha256"],
                                   "grids": series, "assessment": assessment})
        report["passed"] = report["passed"] and assessment["passed"]
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def generate_reference(
    *,
    critic2: Path,
    fixtures: list[tuple[str, Path]],
    manifest: Path,
    output: Path,
    critic_home: Path | None,
    lebedev_points: int,
    mapping_tolerance_bohr: float,
    source_commit: str,
    build_description: str,
) -> dict[str, object]:
    hashes = _manifest_hashes(manifest)
    records: list[dict[str, object]] = []

    raw_directory = output.with_suffix(".raw")
    raw_directory.mkdir(parents=True, exist_ok=True)
    for identifier, path in fixtures:
        if identifier not in hashes:
            raise ValueError(f"Fixture {identifier!r} has no active hash in {manifest}")
        observed_hash = verify_fixture_sha256(path, hashes[identifier])
        command_input, stdout, stderr = _run_critic2(
            critic2,
            path,
            lebedev_points=lebedev_points,
            critic_home=critic_home,
        )
        if not re.fullmatch(r"[A-Za-z0-9_-]+", identifier):
            raise ValueError("Reference fixture identifiers must be safe filenames")
        (raw_directory / f"{identifier}.out").write_text(stdout, encoding="utf-8")
        (raw_directory / f"{identifier}.cri").write_text(command_input, encoding="utf-8")
        (raw_directory / f"{identifier}.err").write_text(stderr, encoding="utf-8")
        numbers, positions_bohr, charge = _calculation_geometry(path)
        parsed = parse_critic2_basin_output(stdout)
        ordered = map_critic2_rows_to_atoms(
            parsed,
            numbers,
            positions_bohr,
            tolerance_bohr=mapping_tolerance_bohr,
        )
        populations = [float(row.population) for row in ordered]
        diagnostics = validate_reference_populations(
            populations, expected_electrons=float(sum(numbers) - charge)
        )
        charges = [float(z) - pop for z, pop in zip(numbers, populations)]
        records.append(
            {
                "id": identifier,
                "path": str(path.as_posix()),
                "sha256": observed_hash,
                "atom_count": int(len(numbers)),
                "atomic_numbers": [int(value) for value in numbers],
                "critic2_attractor_positions_bohr": [
                    [float(value) for value in row.position_bohr] for row in ordered
                ],
                "populations_e": populations,
                "charges_e": charges,
                "population_sum_e": float(sum(populations)),
                "expected_electrons_e": diagnostics["expected_electrons_e"],
                "population_closure_residual_e": diagnostics["electron_count_residual_e"],
                "charge_sum_e": float(sum(charges)),
                "expected_molecular_charge_e": float(charge),
                "reference_diagnostics": diagnostics,
                "critic2_input": command_input,
                "critic2_stderr": stderr,
                "critic2_stdout_sha256": hashlib.sha256(stdout.encode("utf-8")).hexdigest(),
            }
        )

    payload: dict[str, object] = {
        "schema_version": 1,
        "reference_program": "Critic2",
        "critic2_release": CRITIC2_RELEASE,
        "critic2_source_commit": source_commit,
        "integration_method": "molecular bisection",
        "angular_quadrature": {"kind": "Lebedev", "points": int(lebedev_points)},
        "mapping_tolerance_bohr": float(mapping_tolerance_bohr),
        "reference_population_closure_tolerance_e": REFERENCE_POPULATION_CLOSURE_TOLERANCE_E,
        "build_provenance": build_description,
        "fixtures": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _parse_fixture(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("fixture must be ID=PATH")
    identifier, raw_path = value.split("=", 1)
    if not identifier.strip() or not raw_path.strip():
        raise argparse.ArgumentTypeError("fixture must be ID=PATH")
    return identifier.strip(), Path(raw_path.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--critic2", type=Path, required=True)
    parser.add_argument("--critic-home", type=Path)
    parser.add_argument("--manifest", type=Path, default=Path("validation/manifest.json"))
    parser.add_argument("--fixture", action="append", type=_parse_fixture, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lebedev-points", type=int, default=DEFAULT_LEBEDEV_POINTS)
    parser.add_argument("--mapping-tolerance-bohr", type=float, default=0.35)
    parser.add_argument("--critic2-source-commit", default=CRITIC2_COMMIT)
    parser.add_argument("--build-description", default="not recorded")
    parser.add_argument("--compare-openwfn", action="store_true",
                        help="Require independent agreement and coarse/medium/fine convergence")
    args = parser.parse_args()

    if args.lebedev_points <= 0:
        parser.error("--lebedev-points must be positive")
    payload = generate_reference(
        critic2=args.critic2,
        fixtures=args.fixture,
        manifest=args.manifest,
        output=args.output,
        critic_home=args.critic_home,
        lebedev_points=args.lebedev_points,
        mapping_tolerance_bohr=args.mapping_tolerance_bohr,
        source_commit=args.critic2_source_commit,
        build_description=args.build_description,
    )
    if args.compare_openwfn:
        comparison = compare_openwfn_reference(payload, args.output.with_suffix(".comparison.json"))
        if not comparison["passed"]:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
