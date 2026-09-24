#!/usr/bin/env python3
"""Capture normalized FCHK parser evidence from qc-iodata."""

from __future__ import annotations

import argparse
import json
import math
import sys
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from typing import Any, Callable


def _float_list(values: Any) -> list[float]:
    return [float(value) for value in values]


def _float_matrix(values: Any) -> list[list[float]]:
    return [_float_list(row) for row in values]


def _require_integer(value: Any, name: str) -> int:
    number = float(value)
    rounded = round(number)
    if not math.isfinite(number) or not math.isclose(number, rounded, abs_tol=1e-8):
        raise ValueError(f"{name} must be a finite integer")
    return int(rounded)


def _validate_finite(value: Any) -> None:
    if isinstance(value, dict):
        for item in value.values():
            _validate_finite(item)
    elif isinstance(value, list):
        for item in value:
            _validate_finite(item)
    elif isinstance(value, (int, float)) and not math.isfinite(float(value)):
        raise ValueError("reference output must contain only finite numbers")


def build_reference(
    input_path: Path,
    loader: Callable[[str], Any],
    program_version: str,
) -> dict[str, object]:
    """Normalize the independent parser's public data model."""

    data = loader(str(input_path))
    if (
        data.mo is None
        or data.mo.energiesa is None
        or data.mo.energiesb is None
        or data.mo.occsa is None
        or data.mo.occsb is None
    ):
        raise ValueError("qc-iodata did not provide complete orbital evidence")
    if len(data.mo.energiesa) != len(data.mo.occsa) or len(data.mo.energiesb) != len(
        data.mo.occsb
    ):
        raise ValueError("orbital energies and occupations must have equal lengths")
    spin_polarization = data.spinpol
    if spin_polarization is None:
        spin_polarization = data.mo.spinpol
    spin_polarization = _require_integer(spin_polarization, "spin polarization")
    if spin_polarization < 0:
        raise ValueError("spin polarization must be non-negative")
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "program": "qc-iodata",
        "program_version": str(program_version),
        "input_sha256": sha256(input_path.read_bytes()).hexdigest(),
        "energy_hartree": float(data.energy),
        "charge": _require_integer(data.charge, "charge"),
        "multiplicity": spin_polarization + 1,
        "atomic_numbers": [int(value) for value in data.atnums],
        "coordinates_bohr": _float_matrix(data.atcoords),
        "orbital_kind": str(data.mo.kind),
        "alpha_orbital_energies_hartree": _float_list(data.mo.energiesa),
        "beta_orbital_energies_hartree": _float_list(data.mo.energiesb),
        "alpha_orbital_occupations": _float_list(data.mo.occsa),
        "beta_orbital_occupations": _float_list(data.mo.occsb),
    }
    _validate_finite(payload)
    return payload


def write_reference(
    payload: dict[str, object], output_path: Path, *, overwrite: bool = False
) -> None:
    """Write deterministic normalized evidence without accidental replacement."""

    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Output exists: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def capture(input_path: Path, output_path: Path, *, overwrite: bool = False) -> None:
    """Load qc-iodata lazily so it remains outside runtime dependencies."""

    try:
        import iodata
    except ImportError as exc:
        raise RuntimeError("Install qc-iodata==1.0.1 in the benchmark environment") from exc
    program_version = getattr(iodata, "__version__", None) or version("qc-iodata")
    payload = build_reference(input_path, iodata.load_one, program_version)
    write_reference(payload, output_path, overwrite=overwrite)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        capture(args.input, args.output, overwrite=args.overwrite)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 6
    except (FileExistsError, OSError, TypeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
