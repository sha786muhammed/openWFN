"""Extract source-reported properties without requiring a complete wavefunction."""

import logging
import sys
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from .errors import DataUnavailableError
from .results import ResultRecord


def _normalize_output(parsed: Any) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Normalize selected cclib fields; no electronic properties are inferred."""
    metadata = getattr(parsed, "metadata", {}) or {}
    warnings: list[str] = []
    data: dict[str, Any] = {
        "source_program": metadata.get("package"),
        "source_program_version": metadata.get("package_version"),
        "methods": list(metadata.get("methods", [])),
        "basis_set": metadata.get("basis_set"),
        "normal_termination": metadata.get("success"),
        "atom_count": getattr(parsed, "natom", None),
        "charge": getattr(parsed, "charge", None),
        "multiplicity": getattr(parsed, "mult", None),
        "scf_energy_hartree": None,
        "atomic_numbers": None,
        "coordinates_angstrom": None,
        "dipole_debye": None,
        "dipole_origin_angstrom": None,
        "frontier_orbitals": [],
        "reported_atomic_charges": {},
    }
    # cclib stores energies in eV using this conversion constant.
    energies = getattr(parsed, "scfenergies", None)
    if energies is not None and np.size(energies):
        data["scf_energy_hartree"] = float(np.asarray(energies).reshape(-1)[-1]) / 27.21138505
    coordinates = getattr(parsed, "atomcoords", None)
    numbers = getattr(parsed, "atomnos", None)
    if coordinates is not None and numbers is not None:
        frames = np.asarray(coordinates, dtype=float)
        atomnos = np.asarray(numbers)
        if frames.ndim != 3 or frames.shape[0] == 0 or frames.shape[1:] != (data["atom_count"], 3):
            raise ValueError("Output coordinates are inconsistent with atom_count")
        if atomnos.shape != (data["atom_count"],):
            raise ValueError("Output atomic numbers are inconsistent with atom_count")
        data["coordinates_angstrom"] = frames[-1].tolist()
        data["atomic_numbers"] = atomnos.tolist()
    moments = getattr(parsed, "moments", None)
    if moments is not None and len(moments) >= 2:
        origin = np.asarray(moments[0], dtype=float)
        dipole = np.asarray(moments[1], dtype=float)
        if origin.shape != (3,) or dipole.shape != (3,):
            raise ValueError("Output dipole and origin must have three components")
        data["dipole_origin_angstrom"] = origin.tolist()
        data["dipole_debye"] = dipole.tolist()
    orbital_energies = getattr(parsed, "moenergies", None)
    homos = getattr(parsed, "homos", None)
    if orbital_energies is not None and homos is not None:
        if len(orbital_energies) != len(homos) or len(homos) not in {1, 2}:
            raise ValueError("Output orbital channels and HOMO indices are inconsistent")
        for channel, (values, index) in enumerate(zip(orbital_energies, homos, strict=True)):
            values = np.asarray(values, dtype=float)
            homo = int(index)
            if homo != index or values.ndim != 1:
                raise ValueError("Output HOMO index or orbital array is invalid")
            if homo < 0:
                warnings.append(f"Orbital channel {channel} has no occupied orbital.")
                continue
            if homo >= len(values):
                raise ValueError("Output HOMO index exceeds available orbitals")
            has_lumo = homo + 1 < len(values)
            data["frontier_orbitals"].append({
                "channel": "restricted_or_alpha" if len(homos) == 1 else ("alpha", "beta")[channel],
                "homo_index_1based": homo + 1,
                "lumo_index_1based": homo + 2 if has_lumo else None,
                "homo_ev": float(values[homo]),
                "lumo_ev": float(values[homo + 1]) if has_lumo else None,
                "gap_ev": float(values[homo + 1] - values[homo]) if has_lumo else None,
            })
            if not has_lumo:
                warnings.append(f"Orbital channel {channel} has no reported unoccupied orbital.")
    for method, values in (getattr(parsed, "atomcharges", {}) or {}).items():
        charges = np.asarray(values, dtype=float)
        if charges.shape != (data["atom_count"],):
            raise ValueError(f"Reported {method} charges are inconsistent with atom_count")
        total = float(charges.sum())
        residual = total - data["charge"] if data["charge"] is not None else None
        data["reported_atomic_charges"][str(method)] = {
            "charges": charges.tolist(),
            "total_charge": total,
            "charge_sum_residual": residual,
        }
        if residual is not None and abs(residual) > 1e-4:
            warnings.append(f"Reported {method} charges do not sum to the molecular charge within 1e-4 e.")
    if data["normal_termination"] is not True:
        warnings.append("Normal job termination was not confirmed; properties may be incomplete.")
    if data["scf_energy_hartree"] is None:
        warnings.append("No SCF energy was reported by the reader.")
    return data, tuple(warnings)


def read_output(path: str | Path) -> ResultRecord:
    """Read QC text output into a source-reported property result.

    Requires the optional ``outputs`` extra. Missing fields remain null or empty.
    SCF energy is in hartree; coordinates/origin in angstrom; dipole in Debye;
    orbital energies in eV and charges in elementary-charge units. Orbital indices
    are 1-based. Normal termination does not establish optimization convergence.
    Raises DataUnavailableError for missing readers or unrecognized output, and
    ValueError for malformed/nonfinite data. This does not compute a wavefunction.
    """
    try:
        from cclib.io import ccread
    except ImportError as exc:
        raise DataUnavailableError(
            "Output properties require cclib; install openwfn[outputs]."
        ) from exc
    source = Path(path)
    content = source.read_bytes()
    started = perf_counter()
    parsed = ccread(str(source), loglevel=logging.ERROR, logstream=sys.stderr)
    if parsed is None:
        raise DataUnavailableError("The output program was not recognized by cclib.")
    # Avoid associating properties with a hash of a different file version.
    if source.read_bytes() != content:
        raise ValueError("Input changed while output properties were being read")
    data, warnings = _normalize_output(parsed)
    if data["atom_count"] is None and data["scf_energy_hartree"] is None:
        raise DataUnavailableError("No molecular or energy properties were parsed from this output.")
    return ResultRecord(
        kind="output_properties",
        data=data,
        status="partial" if warnings else "success",
        validation_status="Experimental",
        units={
            "scf_energy_hartree": "hartree",
            "coordinates_angstrom": "angstrom",
            "dipole_origin_angstrom": "angstrom",
            "dipole_debye": "Debye",
            "frontier_orbitals": "energies: eV; indices: 1-based",
            "reported_atomic_charges": "e",
        },
        warnings=warnings,
        provenance={
            "property_origin": "source-reported",
            "source_path": str(source.resolve()),
            "input_sha256": sha256(content).hexdigest(),
            "parser": "cclib",
            "parser_version": version("cclib"),
            "openwfn_version": version("openwfn"),
            "source_program": data["source_program"],
            "source_program_version": data["source_program_version"],
            "transformations": ["SCF energy converted eV -> hartree using cclib's conversion constant"],
        },
        elapsed_seconds=perf_counter() - started,
    )
