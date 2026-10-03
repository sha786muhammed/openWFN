"""Source-faithful excited-state extraction from Q-Chem text output."""

from __future__ import annotations

import re
from math import isfinite

from ...constants import SYMBOL_TO_Z
from ...excited_states import (
    MAX_EXCITED_STATES_PER_JOB,
    ExcitedState,
    ExcitedStateCollection,
    ExcitedStateJob,
)
from .conventions import classify_method

_FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"
_JOB_SPLIT_RE = re.compile(r"(?m)^\s*@@@\s*$")
_VERSION_RE = re.compile(r"Q-?Chem\s+([^\s]+)", re.IGNORECASE)
_CHARGE_MULT_RE = re.compile(
    r"Charge\s*=\s*(-?\d+)\s+Multiplicity\s*=\s*(\d+)", re.IGNORECASE
)
_ENERGY_RE = re.compile(
    rf"Total\s+energy\s+in\s+the\s+final\s+basis\s+set\s*=\s*({_FLOAT})",
    re.IGNORECASE,
)
_STATE_RE = re.compile(
    rf"(?im)^\s*Excited\s+state\s+(\d+)\s*:\s*"
    rf"(?:excitation\s+energy\s*\(eV\)\s*=\s*)?({_FLOAT})"
    rf"(?:\s*eV)?\s*$",
)
_MULT_RE = re.compile(r"(?im)^\s*Multiplicity\s*:\s*([^\s]+)")
_SYMM_RE = re.compile(r"(?im)^\s*(?:State\s+)?Symmetry\s*:\s*(\S+)")
_TM_RE = re.compile(
    rf"(?im)^\s*Trans\.\s*Mom\.\s*:\s*({_FLOAT})\s*X\s*"
    rf"({_FLOAT})\s*Y\s*({_FLOAT})\s*Z\s*$"
)
_TM_ALT_RE = re.compile(
    rf"(?im)^\s*(?:Transition\s+)?Dipole(?:\s+Moment)?\s*:\s*"
    rf"X\s*=\s*({_FLOAT})\s+Y\s*=\s*({_FLOAT})\s+Z\s*=\s*({_FLOAT})\s*$"
)
_STRENGTH_RE = re.compile(
    rf"(?im)^\s*(?:Strength|Oscillator\s+Strength)\s*:?(?:\s*=)?\s*({_FLOAT})\s*$"
)
_GEOM_START_RE = re.compile(r"Standard\s+Nuclear\s+Orientation\s*\(Angstroms\)", re.IGNORECASE)
_GEOM_ROW_RE = re.compile(
    rf"^\s*\d+\s+([A-Za-z]{{1,3}})\s+({_FLOAT})\s+({_FLOAT})\s+({_FLOAT})\s*$"
)
_REM_RE = re.compile(r"(?is)\$rem\s*(.*?)\$end")
_METHOD_LINE_RE = re.compile(r"(?im)^\s*METHOD\s+(.+?)\s*$")

_MULTIPLICITIES = {
    "singlet": 1,
    "doublet": 2,
    "triplet": 3,
    "quartet": 4,
    "quintet": 5,
    "sextet": 6,
    "septet": 7,
    "octet": 8,
}


def _as_float(value: str) -> float:
    number = float(value.replace("D", "E").replace("d", "e"))
    if not isfinite(number):
        raise ValueError("Q-Chem excited-state numeric value must be finite")
    return number


def _split_jobs(text: str) -> tuple[str, ...]:
    return tuple(segment for segment in _JOB_SPLIT_RE.split(text) if segment.strip())


def _method_detail(segment: str) -> str:
    rem = _REM_RE.search(segment)
    if rem is not None:
        method = _METHOD_LINE_RE.search(rem.group(1))
        if method is not None:
            return method.group(1).strip()
    for line in segment.splitlines():
        upper = line.upper()
        if "EXCITATION ENERG" in upper and line.strip():
            return line.strip()
    return "Q-Chem excited-state output"


def _classification_label(segment: str, detail: str) -> str:
    """Add only method-control context, never property labels such as ``Trans. Mom.``."""

    upper = segment.upper()
    markers: list[str] = []
    for marker in (
        "TDDFT",
        "TDA",
        "EOM-EE",
        "EOM-IP",
        "EOM-EA",
        "EOM-SF",
        "ADC",
        "RAS-SF",
        "STEX",
        "CASSCF",
        "CASPT2",
        "NEVPT2",
        "NOCI",
    ):
        if marker in upper:
            markers.append(marker)
    if "CIS_N_ROOTS" in upper and not any(
        marker in markers for marker in ("EOM-EE", "EOM-IP", "EOM-EA", "EOM-SF", "ADC")
    ):
        markers.append("TDDFT")
    return " ".join((detail, *markers))


def _method_family(segment: str, detail: str) -> str:
    return classify_method("Q-Chem", _classification_label(segment, detail)).family


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
            if started and line.strip().startswith("-"):
                break
            continue
        started = True
        symbol = match.group(1)[0].upper() + match.group(1)[1:].lower()
        atomic_number = SYMBOL_TO_Z.get(symbol)
        if atomic_number is None:
            raise ValueError(f"Unknown Q-Chem element symbol {symbol!r} in nuclear orientation")
        atomic_numbers.append(atomic_number)
        coordinates.append(tuple(_as_float(match.group(i)) for i in (2, 3, 4)))
    return tuple(atomic_numbers), tuple(coordinates)


def _multiplicity(value: str | None) -> int | None:
    if value is None:
        return None
    clean = value.strip().casefold()
    if clean.isdigit():
        number = int(clean)
        return number if number > 0 else None
    return _MULTIPLICITIES.get(clean)


def _parse_states(segment: str) -> tuple[ExcitedState, ...]:
    headers = list(_STATE_RE.finditer(segment))
    if len(headers) > MAX_EXCITED_STATES_PER_JOB:
        raise ValueError(
            f"state limit exceeded: at most {MAX_EXCITED_STATES_PER_JOB} states per job"
        )
    states: list[ExcitedState] = []
    for index, header in enumerate(headers, start=1):
        end = headers[index].start() if index < len(headers) else len(segment)
        block = segment[header.end() : end]
        mult_match = _MULT_RE.search(block)
        symmetry_match = _SYMM_RE.search(block)
        transition_match = _TM_RE.search(block) or _TM_ALT_RE.search(block)
        strength_match = _STRENGTH_RE.search(block)
        transition_dipole = None
        if transition_match is not None:
            transition_dipole = tuple(_as_float(transition_match.group(i)) for i in (1, 2, 3))
        states.append(
            ExcitedState(
                index=index,
                source_state=header.group(1),
                energy_ev=_as_float(header.group(2)),
                oscillator_strength=(
                    _as_float(strength_match.group(1)) if strength_match is not None else None
                ),
                transition_dipole=transition_dipole,
                transition_dipole_unit="au" if transition_dipole is not None else None,
                multiplicity=_multiplicity(mult_match.group(1) if mult_match is not None else None),
                symmetry=symmetry_match.group(1) if symmetry_match is not None else None,
            )
        )
    return tuple(states)


def parse_qchem_excited_states(text: str) -> ExcitedStateCollection | None:
    """Parse Q-Chem excited-state jobs without merging data across ``@@@`` jobs."""

    jobs: list[ExcitedStateJob] = []
    for source_job_index, segment in enumerate(_split_jobs(text), start=1):
        states = _parse_states(segment)
        if not states:
            continue
        detail = _method_detail(segment)
        charge_match = _CHARGE_MULT_RE.search(segment)
        energy_match = _ENERGY_RE.search(segment)
        version_match = _VERSION_RE.search(segment)
        atomic_numbers, coordinates = _parse_geometry(segment)
        jobs.append(
            ExcitedStateJob(
                index=len(jobs) + 1,
                source_program="Q-Chem",
                source_program_version=(version_match.group(1) if version_match is not None else None),
                method_family=_method_family(segment, detail),
                method_detail=detail,
                states=states,
                source_job_label=str(source_job_index),
                charge=int(charge_match.group(1)) if charge_match is not None else None,
                multiplicity=int(charge_match.group(2)) if charge_match is not None else None,
                reference_energy_hartree=(
                    _as_float(energy_match.group(1)) if energy_match is not None else None
                ),
                atomic_numbers=atomic_numbers,
                coordinates_angstrom=coordinates,
                terminated_normally=(
                    True if "THANK YOU VERY MUCH FOR USING Q-CHEM" in segment.upper() else None
                ),
            )
        )
    if not jobs:
        return None
    return ExcitedStateCollection(
        jobs=tuple(jobs),
        parser_provenance=(("adapter", "openwfn.parsers.excited.qchem"),),
    )
