"""Source-faithful excited-state extraction from ORCA text output."""

from __future__ import annotations

import re

from ...constants import SYMBOL_TO_Z
from ...excited_states import (
    MAX_EXCITED_STATES_PER_JOB,
    ExcitedState,
    ExcitedStateCollection,
    ExcitedStateJob,
)

_FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"
_JOB_RE = re.compile(r"(?m)^\s*JOB\s+NUMBER\s+(\d+)\s*$", re.IGNORECASE)
_ROUTE_RE = re.compile(r"(?m)^\s*!\s*(.+?)\s*$")
_CHARGE_RE = re.compile(r"Total\s+Charge\s*:\s*(-?\d+)", re.IGNORECASE)
_MULT_RE = re.compile(r"Multiplicity\s*:\s*(\d+)", re.IGNORECASE)
_ENERGY_RE = re.compile(rf"FINAL\s+SINGLE\s+POINT\s+ENERGY\s+({_FLOAT})", re.IGNORECASE)
_GENERIC_STATE_RE = re.compile(
    rf"(?m)^\s*STATE\s+(\d+)\s*:\s*E\s*=\s*{_FLOAT}\s+au\s+({_FLOAT})\s+eV\b",
    re.IGNORECASE,
)
_CASSCF_RE = re.compile(
    rf"(?m)^\s*(\d+)\s*:\s+\d+\s+(\d+)\s+(\S+)\s+{_FLOAT}\s+({_FLOAT})\s+{_FLOAT}\s*$"
)
_OPTICAL_RE = re.compile(
    rf"(?m)^\s*(\S+)\s*->\s*(\S+)\s+({_FLOAT})\s+{_FLOAT}\s+{_FLOAT}\s+"
    rf"({_FLOAT})\s+{_FLOAT}\s+({_FLOAT})\s+({_FLOAT})\s+({_FLOAT})\s*$"
)
_GEOM_START_RE = re.compile(r"CARTESIAN\s+COORDINATES\s*\(ANGSTROEM\)", re.IGNORECASE)
_GEOM_ROW_RE = re.compile(rf"^\s*([A-Za-z]{{1,3}})\s+({_FLOAT})\s+({_FLOAT})\s+({_FLOAT})\s*$")


def _as_float(value: str) -> float:
    return float(value.replace("D", "E").replace("d", "e"))


def _split_jobs(text: str) -> list[tuple[str | None, str]]:
    matches = list(_JOB_RE.finditer(text))
    if not matches:
        return [(None, text)]
    chunks: list[tuple[str | None, str]] = []
    prefix = text[: matches[0].start()]
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        chunk = prefix + text[match.start() : end] if index == 0 else text[match.start() : end]
        chunks.append((match.group(1), chunk))
    return chunks


def _method_family(segment: str, detail: str) -> str:
    upper = f"{detail}\n{segment}".upper()
    if "STEOM" in upper:
        return "steom"
    if "EOM" in upper:
        return "eom"
    if "CASSCF" in upper or "CAS-SCF" in upper:
        return "casscf"
    if "NEVPT2" in upper:
        return "nevpt2"
    if "CASPT2" in upper:
        return "caspt2"
    if "ADC" in upper:
        return "adc"
    if "ROCIS" in upper:
        return "rocis"
    if "TD-DFT" in upper or "TDDFT" in upper or "TDA" in upper:
        return "tddft"
    if re.search(r"\bCIS\b", upper):
        return "cis"
    return "other"


def _parse_geometry(segment: str) -> tuple[tuple[int, ...], tuple[tuple[float, float, float], ...]]:
    marker = _GEOM_START_RE.search(segment)
    if marker is None:
        return (), ()
    atomic_numbers: list[int] = []
    coordinates: list[tuple[float, float, float]] = []
    started = False
    for line in segment[marker.end() :].splitlines():
        match = _GEOM_ROW_RE.match(line)
        if match is None:
            if started and not line.strip():
                break
            continue
        started = True
        symbol = match.group(1)[0].upper() + match.group(1)[1:].lower()
        atomic_number = SYMBOL_TO_Z.get(symbol)
        if atomic_number is None:
            raise ValueError(f"Unknown ORCA element symbol {symbol!r} in Cartesian coordinates")
        atomic_numbers.append(atomic_number)
        coordinates.append(tuple(_as_float(match.group(i)) for i in (2, 3, 4)))
    return tuple(atomic_numbers), tuple(coordinates)


def _candidate_count(segment: str) -> int:
    optical = len(_OPTICAL_RE.findall(segment))
    casscf = len(_CASSCF_RE.findall(segment)) if "CASSCF" in segment.upper() else 0
    generic = len(_GENERIC_STATE_RE.findall(segment))
    return max(optical, casscf, generic)


def _parse_states(segment: str) -> tuple[ExcitedState, ...]:
    if _candidate_count(segment) > MAX_EXCITED_STATES_PER_JOB:
        raise ValueError(
            f"state limit exceeded: at most {MAX_EXCITED_STATES_PER_JOB} states per job"
        )

    optical_matches = list(_OPTICAL_RE.finditer(segment))
    if optical_matches:
        return tuple(
            ExcitedState(
                index=index,
                source_state=match.group(2),
                energy_ev=_as_float(match.group(3)),
                oscillator_strength=_as_float(match.group(4)),
                transition_dipole=(
                    _as_float(match.group(5)),
                    _as_float(match.group(6)),
                    _as_float(match.group(7)),
                ),
                transition_dipole_unit="au",
            )
            for index, match in enumerate(optical_matches, start=1)
        )

    if "CASSCF" in segment.upper():
        casscf_matches = list(_CASSCF_RE.finditer(segment))
        if casscf_matches:
            return tuple(
                ExcitedState(
                    index=index,
                    source_state=match.group(1),
                    energy_ev=_as_float(match.group(4)),
                    multiplicity=int(match.group(2)),
                    symmetry=match.group(3),
                )
                for index, match in enumerate(casscf_matches, start=1)
            )

    generic_matches = list(_GENERIC_STATE_RE.finditer(segment))
    return tuple(
        ExcitedState(
            index=index,
            source_state=match.group(1),
            energy_ev=_as_float(match.group(2)),
        )
        for index, match in enumerate(generic_matches, start=1)
    )


def parse_orca_excited_states(text: str) -> ExcitedStateCollection | None:
    """Parse source-reported ORCA excited states without inventing unavailable properties."""

    jobs: list[ExcitedStateJob] = []
    for source_job_label, segment in _split_jobs(text):
        states = _parse_states(segment)
        if not states:
            continue
        route_match = _ROUTE_RE.search(segment)
        method_detail = route_match.group(1).strip() if route_match else "ORCA excited-state output"
        charge_match = _CHARGE_RE.search(segment)
        multiplicity_match = _MULT_RE.search(segment)
        energy_match = _ENERGY_RE.search(segment)
        atomic_numbers, coordinates = _parse_geometry(segment)
        jobs.append(
            ExcitedStateJob(
                index=len(jobs) + 1,
                source_program="ORCA",
                method_family=_method_family(segment, method_detail),
                method_detail=method_detail,
                states=states,
                source_job_label=source_job_label,
                charge=int(charge_match.group(1)) if charge_match else None,
                multiplicity=int(multiplicity_match.group(1)) if multiplicity_match else None,
                reference_energy_hartree=_as_float(energy_match.group(1)) if energy_match else None,
                atomic_numbers=atomic_numbers,
                coordinates_angstrom=coordinates,
                terminated_normally=True if "ORCA TERMINATED NORMALLY" in segment.upper() else None,
            )
        )

    if not jobs:
        return None
    return ExcitedStateCollection(
        jobs=tuple(jobs),
        parser_provenance=(("adapter", "openwfn.parsers.excited.orca"),),
    )
