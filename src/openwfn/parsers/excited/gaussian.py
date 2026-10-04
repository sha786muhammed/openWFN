"""Source-faithful Gaussian excited-state text parsing."""

import re
from math import isfinite

from ...excited_states import (
    MAX_EXCITED_STATES_PER_JOB,
    ExcitedState,
    ExcitedStateCollection,
    ExcitedStateJob,
    TransitionContribution,
)

_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[DEde][-+]?\d+)?"
_STATE = re.compile(
    rf"^\s*Excited State\s+(?P<state>\d+)\s*:\s*(?P<label>.*?)\s+"
    rf"(?P<energy>{_NUMBER})\s+eV(?:\s+{_NUMBER}\s+nm)?"
    rf"(?:\s+f\s*=\s*(?P<f>{_NUMBER}))?"
    rf"(?:\s+<S\*\*2>\s*=\s*(?P<s2>{_NUMBER}))?",
    re.IGNORECASE,
)
_CONTRIBUTION = re.compile(
    rf"^\s*(?P<source>\S+)\s*->\s*(?P<target>\S+)\s+(?P<value>{_NUMBER})\s*$"
)
_CHARGE_MULTIPLICITY = re.compile(
    r"Charge\s*=\s*(-?\d+)\s+Multiplicity\s*=\s*(\d+)", re.IGNORECASE
)
_SCF_ENERGY = re.compile(rf"SCF Done:\s+E\([^)]+\)\s*=\s*({_NUMBER})")

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


def _float(value: str) -> float:
    number = float(value.replace("D", "E").replace("d", "e"))
    if not isfinite(number):
        raise ValueError("Gaussian excited-state numeric value must be finite")
    return number


def _split_jobs(text: str) -> tuple[str, ...]:
    blocks = re.split(r"(?im)^\s*--Link1--\s*$", text)
    return tuple(block for block in blocks if block.strip())


def _route(lines: list[str]) -> str:
    route_lines = [line.strip() for line in lines if line.lstrip().startswith("#")]
    return " ".join(route_lines) if route_lines else "Gaussian excited-state output"


def _method_family(route: str) -> str:
    lowered = route.casefold()
    if re.search(r"(?:^|[\s/#(])cis(?:[\s/(),]|$)", lowered):
        return "cis"
    if "td(" in lowered or re.search(r"(?:^|\s)td(?:\s|/|$)", lowered) or "tda" in lowered:
        return "tddft"
    return "other"


def _is_dash(line: str) -> bool:
    stripped = line.strip()
    return len(stripped) >= 5 and set(stripped) == {"-"}


def _parse_orientation(
    lines: list[str], start: int
) -> tuple[tuple[int, tuple[float, float, float]], ...] | None:
    index = start + 1
    dash_count = 0
    while index < len(lines):
        if _is_dash(lines[index]):
            dash_count += 1
            if dash_count == 2:
                index += 1
                break
        index += 1
    if dash_count < 2:
        return None

    rows: list[tuple[int, tuple[float, float, float]]] = []
    while index < len(lines) and not _is_dash(lines[index]):
        tokens = lines[index].split()
        if len(tokens) >= 6:
            try:
                atomic_number = int(tokens[1])
                coordinates = (_float(tokens[3]), _float(tokens[4]), _float(tokens[5]))
            except ValueError:
                return None
            rows.append((atomic_number, coordinates))
        index += 1
    return tuple(rows) if rows else None


def _geometry_before(
    lines: list[str], state_line: int
) -> tuple[tuple[int, ...], tuple[tuple[float, float, float], ...]]:
    candidates: list[tuple[tuple[int, tuple[float, float, float]], ...]] = []
    for index, line in enumerate(lines[:state_line]):
        if "Standard orientation:" in line or "Input orientation:" in line:
            parsed = _parse_orientation(lines, index)
            if parsed is not None:
                candidates.append(parsed)
    if not candidates:
        return (), ()
    selected = candidates[-1]
    return (
        tuple(item[0] for item in selected),
        tuple(item[1] for item in selected),
    )


def _multiplicity_and_symmetry(label: str) -> tuple[int | None, str | None]:
    clean = label.strip()
    lowered = clean.casefold()
    multiplicity = next(
        (value for name, value in _MULTIPLICITIES.items() if lowered.startswith(name)), None
    )
    symmetry: str | None = None
    if "-" in clean:
        candidate = clean.split("-", maxsplit=1)[1].strip()
        if candidate and candidate != "?":
            symmetry = candidate
    return multiplicity, symmetry


def _transition_dipoles(lines: list[str]) -> dict[int, tuple[float, float, float]]:
    table_start = next(
        (
            index
            for index, line in enumerate(lines)
            if "Ground to excited state transition electric dipole moments" in line
        ),
        None,
    )
    if table_start is None:
        return {}
    result: dict[int, tuple[float, float, float]] = {}
    found_row = False
    for line in lines[table_start + 1 :]:
        tokens = line.split()
        if len(tokens) >= 4 and tokens[0].isdigit():
            try:
                state = int(tokens[0])
                result[state] = (_float(tokens[1]), _float(tokens[2]), _float(tokens[3]))
            except ValueError:
                if found_row:
                    break
                continue
            found_row = True
        elif found_row and line.strip():
            break
    return result


def _job_metadata(
    lines: list[str], first_state_line: int
) -> tuple[int | None, int | None, float | None]:
    charge: int | None = None
    multiplicity: int | None = None
    energy: float | None = None
    for line in lines[: first_state_line + 1]:
        charge_match = _CHARGE_MULTIPLICITY.search(line)
        if charge_match:
            charge = int(charge_match.group(1))
            multiplicity = int(charge_match.group(2))
        energy_match = _SCF_ENERGY.search(line)
        if energy_match:
            energy = _float(energy_match.group(1))
    return charge, multiplicity, energy


def _parse_job(block: str, job_index: int) -> ExcitedStateJob | None:
    lines = block.splitlines()
    headers: list[tuple[int, re.Match[str]]] = []
    for line_index, line in enumerate(lines):
        match = _STATE.match(line)
        if match is not None:
            headers.append((line_index, match))
            if len(headers) > MAX_EXCITED_STATES_PER_JOB:
                raise ValueError(
                    f"state limit exceeded: at most {MAX_EXCITED_STATES_PER_JOB} states per job"
                )
    if not headers:
        return None

    route = _route(lines)
    dipoles = _transition_dipoles(lines)
    atomic_numbers, coordinates = _geometry_before(lines, headers[0][0])
    charge, multiplicity, energy = _job_metadata(lines, headers[0][0])
    states: list[ExcitedState] = []

    for offset, (line_index, match) in enumerate(headers):
        source_state = int(match.group("state"))
        end = headers[offset + 1][0] if offset + 1 < len(headers) else len(lines)
        contributions: list[TransitionContribution] = []
        for line in lines[line_index + 1 : end]:
            contribution = _CONTRIBUTION.match(line)
            if contribution is not None:
                contributions.append(
                    TransitionContribution(
                        source_label=contribution.group("source"),
                        target_label=contribution.group("target"),
                        value=_float(contribution.group("value")),
                        quantity="coefficient",
                        convention="Gaussian printed transition coefficient",
                    )
                )

        label = match.group("label").strip()
        state_multiplicity, symmetry = _multiplicity_and_symmetry(label)
        oscillator_strength = (
            _float(match.group("f")) if match.group("f") is not None else None
        )
        spin_expectation = (
            _float(match.group("s2")) if match.group("s2") is not None else None
        )
        transition_dipole = dipoles.get(source_state)
        states.append(
            ExcitedState(
                index=offset + 1,
                source_state=str(source_state),
                energy_ev=_float(match.group("energy")),
                oscillator_strength=oscillator_strength,
                transition_dipole=transition_dipole,
                transition_dipole_unit="au" if transition_dipole is not None else None,
                multiplicity=state_multiplicity,
                symmetry=symmetry,
                label=label or None,
                spin_expectation=spin_expectation,
                contributions=tuple(contributions),
            )
        )

    return ExcitedStateJob(
        index=job_index,
        source_program="Gaussian",
        method_family=_method_family(route),
        method_detail=route,
        states=tuple(states),
        charge=charge,
        multiplicity=multiplicity,
        reference_energy_hartree=energy,
        atomic_numbers=atomic_numbers,
        coordinates_angstrom=coordinates,
        terminated_normally=any("Normal termination of Gaussian" in line for line in lines),
    )


def parse_gaussian_excited_states(text: str) -> ExcitedStateCollection | None:
    """Parse Gaussian excited-state jobs without merging Link1 metadata."""

    jobs: list[ExcitedStateJob] = []
    for block in _split_jobs(text):
        parsed = _parse_job(block, len(jobs) + 1)
        if parsed is not None:
            jobs.append(parsed)
    if not jobs:
        return None
    return ExcitedStateCollection(
        jobs=tuple(jobs),
        parser_provenance=(("parser", "openwfn-gaussian-excited"),),
    )
