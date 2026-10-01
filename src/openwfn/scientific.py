"""Shared scientific semantics derived from source calculation data."""

from dataclasses import dataclass
from typing import Literal

from .errors import DataUnavailableError
from .model import Atom, CalculationData

OrbitalReferenceKind = Literal[
    "restricted_closed_shell",
    "restricted_open_shell",
    "unrestricted",
    "unknown",
]


@dataclass(frozen=True, slots=True)
class ElectronExpectation:
    """Expected integrated electron count and how it was obtained."""

    value: float
    source: str
    warnings: tuple[str, ...] = ()


def effective_nuclear_charge(atom: Atom) -> float:
    """Return source effective nuclear charge, falling back to element identity."""

    if atom.nuclear_charge is not None:
        return float(atom.nuclear_charge)
    return float(atom.atomic_number)


def is_ghost_atom(atom: Atom, tolerance: float = 1e-12) -> bool:
    """Return whether an explicitly charged source center is a ghost center."""

    if tolerance < 0.0:
        raise ValueError("ghost tolerance must be non-negative")
    return atom.nuclear_charge is not None and abs(float(atom.nuclear_charge)) <= tolerance


def expected_electron_count(data: CalculationData, kind: str) -> ElectronExpectation:
    """Return the authoritative expected electron count for one density channel."""

    if kind not in {"total", "alpha", "beta", "spin"}:
        raise ValueError("density kind must be 'total', 'alpha', 'beta', or 'spin'")

    if kind == "total":
        total = data.records.get("Number of electrons")
        if isinstance(total, (int, float)):
            return ElectronExpectation(float(total), "Number of electrons")

        if all(atom.nuclear_charge is not None for atom in data.molecule.atoms):
            value = sum(effective_nuclear_charge(atom) for atom in data.molecule.atoms)
            value -= data.molecule.charge
            return ElectronExpectation(float(value), "effective nuclear charges")

        value = sum(atom.atomic_number for atom in data.molecule.atoms) - data.molecule.charge
        return ElectronExpectation(
            float(value),
            "atomic-number fallback",
            (
                "Expected electron count fell back to atomic numbers because source nuclear charges and Number of electrons were unavailable.",
            ),
        )

    alpha = data.records.get("Number of alpha electrons")
    beta = data.records.get("Number of beta electrons")
    if kind == "alpha" and isinstance(alpha, (int, float)):
        return ElectronExpectation(float(alpha), "Number of alpha electrons")
    if kind == "beta" and isinstance(beta, (int, float)):
        return ElectronExpectation(float(beta), "Number of beta electrons")
    if kind == "spin" and isinstance(alpha, (int, float)) and isinstance(beta, (int, float)):
        return ElectronExpectation(float(alpha - beta), "alpha-beta electron counts")

    if data.alpha_orbitals is not None and data.beta_orbitals is not None:
        alpha_occupation = float(sum(data.alpha_orbitals.occupations))
        beta_occupation = float(sum(data.beta_orbitals.occupations))
        if kind == "alpha":
            return ElectronExpectation(alpha_occupation, "alpha orbital occupations")
        if kind == "beta":
            return ElectronExpectation(beta_occupation, "beta orbital occupations")
        return ElectronExpectation(
            alpha_occupation - beta_occupation, "alpha-beta orbital occupations"
        )

    raise DataUnavailableError(f"Expected electron count is unavailable for {kind} density.")


def orbital_reference_kind(data: CalculationData) -> OrbitalReferenceKind:
    """Classify whether orbital data are restricted closed/open shell or unrestricted."""

    if data.beta_orbitals is not None:
        return "unrestricted"
    alpha = data.records.get("Number of alpha electrons")
    beta = data.records.get("Number of beta electrons")
    if isinstance(alpha, (int, float)) and isinstance(beta, (int, float)):
        return "restricted_closed_shell" if float(alpha) == float(beta) else "restricted_open_shell"
    return "unknown"
