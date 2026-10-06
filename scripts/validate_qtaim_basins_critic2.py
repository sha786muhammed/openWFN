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
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from openwfn.constants import BOHR_TO_ANGSTROM
from openwfn.ingest import load_input

CRITIC2_RELEASE = "1.2"
CRITIC2_COMMIT = "9731d532c6407d35c75bbce5af449211470437a7"
DEFAULT_LEBEDEV_POINTS = 590

_POSITION_HEADER = re.compile(r"Position\s*\(([^)]+)\)", re.IGNORECASE)
_ROW_PREFIX = re.compile(r"^\s*\d+\s+\d+\s+\d+\s+[A-Za-z][A-Za-z0-9]*\s+\d+\s+\d+\s+")
_FLOAT_TOKEN = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?"


@dataclass(frozen=True, slots=True)
class Critic2BasinRow:
    identifier: int
    name: str
    atomic_number: int
    multiplicity: int | None
    position_bohr: tuple[float, float, float]
    volume: float
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
        raise ValueError("Critic2 crystal-coordinate attractors cannot be mapped to molecular atoms")
    raise ValueError(f"Unsupported Critic2 attractor position unit: {unit}")


def _parse_attractor_positions(text: str) -> dict[int, tuple[str, int, int | None, tuple[float, float, float]]]:
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
        if not _ROW_PREFIX.match(line):
            if rows:
                break
            continue
        tokens = line.split()
        if len(tokens) < 9:
            raise ValueError("Critic2 attractor row has too few columns")
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


def _parse_integrated_properties(text: str) -> dict[int, tuple[str, int, int | None, float, float, float]]:
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip().startswith("* Integrated atomic properties"):
            for header_index in range(index + 1, min(index + 10, len(lines))):
                if re.search(r"\bVolume\b", lines[header_index]) and re.search(
                    r"\bPop\b", lines[header_index]
                ):
                    start = header_index + 1
                    break
    if start is None:
        raise ValueError("Critic2 output is missing the integrated atomic-properties table")

    rows: dict[int, tuple[str, int, int | None, float, float, float]] = {}
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("-") or stripped.startswith("Sum"):
            break
        if not stripped or stripped.startswith("#"):
            continue
        if not _ROW_PREFIX.match(line):
            if rows:
                break
            continue
        tokens = line.split()
        if len(tokens) < 9:
            raise ValueError("Critic2 integrated-property row has too few columns")
        identifier = int(tokens[0])
        if identifier in rows:
            raise ValueError(f"Critic2 integrated-property table contains duplicate id {identifier}")
        name = tokens[3]
        atomic_number = int(tokens[4])
        multiplicity = int(tokens[5])
        volume = _parse_float(tokens[6])
        population = _parse_float(tokens[7])
        laplacian = _parse_float(tokens[8])
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
        values = (*position_bohr, volume, population, laplacian)
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

    with tempfile.TemporaryDirectory(prefix="openwfn-qtaim-critic2-") as tmp:
        tmp_path = Path(tmp)
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
            (tmp_path / f"{identifier}.out").write_text(stdout, encoding="utf-8")
            numbers, positions_bohr, charge = _calculation_geometry(path)
            parsed = parse_critic2_basin_output(stdout)
            ordered = map_critic2_rows_to_atoms(
                parsed,
                numbers,
                positions_bohr,
                tolerance_bohr=mapping_tolerance_bohr,
            )
            populations = [float(row.population) for row in ordered]
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
                    "charge_sum_e": float(sum(charges)),
                    "expected_molecular_charge_e": float(charge),
                    "critic2_input": command_input,
                    "critic2_stderr": stderr,
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
    args = parser.parse_args()

    if args.lebedev_points <= 0:
        parser.error("--lebedev-points must be positive")
    generate_reference(
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
