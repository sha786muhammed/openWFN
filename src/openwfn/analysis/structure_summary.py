"""Conservative summary for inputs without a complete molecular wavefunction."""

from ..data import OpenWFNData, StructureData
from ..errors import DataUnavailableError
from ..geometry import molecular_formula
from ..results import ResultRecord


def center_counts(structure: StructureData) -> dict[str, int | None]:
    """Classify centers only when source-provided effective charges allow it."""

    charges = structure.effective_nuclear_charges or (None,) * len(structure.coordinates)
    known = [charge for charge in charges if charge is not None]
    unknown = len(charges) - len(known)
    return {
        "centers": len(charges),
        "physical_nuclei": sum(charge > 0 for charge in known) if known else None,
        "ghost_centers": sum(charge == 0 for charge in known) if known else None,
        "unknown_effective_charges": unknown,
    }


def structure_summary(data: OpenWFNData) -> ResultRecord:
    """Report available structure facts without inferring electronic properties."""

    structure = data.structure
    if structure is None:
        raise DataUnavailableError("Input does not contain an atomic structure.")
    counts = center_counts(structure)
    charges = structure.effective_nuclear_charges or (None,) * len(structure.coordinates)
    complete_identity = counts["unknown_effective_charges"] == 0
    physical_numbers = [
        number for number, charge in zip(structure.atomic_numbers, charges, strict=True)
        if charge is not None and charge > 0 and number is not None
    ]
    formula = (
        molecular_formula(physical_numbers)
        if complete_identity and len(physical_numbers) == counts["physical_nuclei"]
        else None
    )
    warnings = ["No complete molecular wavefunction is available; electronic properties were not inferred."]
    if not complete_identity:
        warnings.append("Some center identities are unknown because effective nuclear charges were absent.")
    return ResultRecord(
        kind="summary",
        status="partial",
        data={
            **counts,
            "atoms": counts["physical_nuclei"],
            "formula": formula,
            "scope": "periodic" if data.periodic is not None else "isolated-structure",
            "charge": structure.charge,
            "multiplicity": structure.multiplicity,
            "energy_hartree": data.metadata.energy_hartree,
            "electron_count": None,
            "center_of_mass": None,
            "bond_count": len(structure.bonds) if structure.bonds else None,
        },
        units={"energy_hartree": "hartree", "center_of_mass": "angstrom"},
        warnings=tuple(warnings),
    )
