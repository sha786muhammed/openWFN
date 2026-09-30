"""Capability inference and requirement evaluation for heterogeneous inputs."""

from dataclasses import dataclass
from typing import Literal

from .data import OpenWFNData

CapabilityState = Literal["available", "derived", "missing", "unsupported"]


@dataclass(frozen=True, slots=True)
class Capability:
    """Availability state for one normalized scientific capability."""

    name: str
    state: CapabilityState
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class CapabilityRequirement:
    """One analysis requirement satisfied by any listed alternative capability."""

    label: str
    alternatives: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("capability requirement label must not be blank")
        if not self.alternatives or any(not item.strip() for item in self.alternatives):
            raise ValueError("capability requirement alternatives must be nonempty")


@dataclass(frozen=True, slots=True)
class RequirementEvaluation:
    """Result of evaluating analysis requirements against one normalized input."""

    available: bool
    missing_requirements: tuple[str, ...]


def _capability(name: str, state: CapabilityState, reason: str | None = None) -> Capability:
    return Capability(name=name, state=state, reason=reason)


def infer_capabilities(data: OpenWFNData) -> dict[str, Capability]:
    """Infer capabilities exclusively from normalized data actually present."""

    calculation = data.calculation
    structure_present = data.structure is not None
    isolated = (
        calculation is not None
        and data.periodic is None
        and calculation.molecule.boundary_conditions.kind == "isolated"
    )
    basis_present = data.basis is not None
    alpha_present = data.alpha_orbitals is not None
    beta_present = data.beta_orbitals is not None
    orbital_occupations = bool(
        (data.alpha_orbitals is not None and data.alpha_orbitals.occupations)
        or (data.beta_orbitals is not None and data.beta_orbitals.occupations)
    )
    metadata_present = calculation is not None or any(
        value is not None
        for value in (
            data.metadata.source_program,
            data.metadata.source_program_version,
            data.metadata.title,
            data.metadata.energy_hartree,
        )
    )
    energy_present = data.metadata.energy_hartree is not None or (
        calculation is not None and calculation.molecule.metadata.energy_hartree is not None
    )

    return {
        "structure": _capability(
            "structure", "available" if structure_present else "missing"
        ),
        "molecular_metadata": _capability(
            "molecular_metadata", "available" if metadata_present else "missing"
        ),
        "isolated_molecule": _capability(
            "isolated_molecule", "available" if isolated else "missing"
        ),
        "periodic_cell": _capability(
            "periodic_cell", "available" if data.periodic is not None else "missing"
        ),
        "basis": _capability("basis", "available" if basis_present else "missing"),
        "alpha_orbitals": _capability(
            "alpha_orbitals", "available" if alpha_present else "missing"
        ),
        "beta_orbitals": _capability(
            "beta_orbitals", "available" if beta_present else "missing"
        ),
        "orbital_occupations": _capability(
            "orbital_occupations", "available" if orbital_occupations else "missing"
        ),
        "total_density": _capability(
            "total_density", "available" if data.total_density is not None else "missing"
        ),
        "spin_density": _capability(
            "spin_density", "available" if data.spin_density is not None else "missing"
        ),
        "ao_overlap": _capability(
            "ao_overlap",
            "derived" if basis_present and isolated else "missing",
            "computed from the normalized basis and isolated molecular geometry"
            if basis_present and isolated
            else None,
        ),
        "volumetric_grid": _capability(
            "volumetric_grid", "available" if data.grids else "missing"
        ),
        "electronic_energy": _capability(
            "electronic_energy", "available" if energy_present else "missing"
        ),
        "integrals": _capability(
            "integrals", "available" if data.integrals is not None else "missing"
        ),
    }


def evaluate_requirements(
    data: OpenWFNData,
    requirements: tuple[CapabilityRequirement, ...],
) -> RequirementEvaluation:
    """Return whether each requirement has at least one available/derived alternative."""

    capabilities = infer_capabilities(data)
    missing: list[str] = []
    for requirement in requirements:
        satisfied = any(
            capabilities.get(alternative, _capability(alternative, "unsupported")).state
            in {"available", "derived"}
            for alternative in requirement.alternatives
        )
        if not satisfied:
            missing.append(requirement.label)
    return RequirementEvaluation(available=not missing, missing_requirements=tuple(missing))
