"""Helpers for attaching typed excited-state records without copying scientific arrays."""

from dataclasses import replace

from ...data import OpenWFNData
from ...excited_states import ExcitedStateCollection
from ...model import Atom, CalculationData, CalculationMetadata, Molecule


def _minimal_calculation(
    data: OpenWFNData,
    collection: ExcitedStateCollection,
) -> CalculationData:
    """Create the smallest source-faithful molecular host for excited-state records."""

    job = collection.jobs[0]
    structure = data.structure
    if structure is not None and all(number is not None for number in structure.atomic_numbers):
        atomic_numbers = tuple(int(number) for number in structure.atomic_numbers)
        coordinates = structure.coordinates
        charge = structure.charge if structure.charge is not None else job.charge
        multiplicity = (
            structure.multiplicity if structure.multiplicity is not None else job.multiplicity
        )
        effective = structure.effective_nuclear_charges or (None,) * len(atomic_numbers)
        bonds = structure.bonds
    elif job.atomic_numbers and job.coordinates_angstrom:
        atomic_numbers = job.atomic_numbers
        coordinates = job.coordinates_angstrom
        charge = job.charge
        multiplicity = job.multiplicity
        effective = (None,) * len(atomic_numbers)
        bonds = ()
    else:
        raise ValueError(
            "Cannot attach excited-state records because no complete molecular structure is available."
        )

    if charge is None or multiplicity is None:
        raise ValueError(
            "Cannot attach excited-state records because charge or multiplicity is unavailable."
        )

    atoms = tuple(
        Atom(
            atomic_number=atomic_number,
            coordinates=coordinate,
            nuclear_charge=effective[index] if index < len(effective) else None,
        )
        for index, (atomic_number, coordinate) in enumerate(
            zip(atomic_numbers, coordinates, strict=True)
        )
    )
    metadata = CalculationMetadata(
        source_program=job.source_program,
        source_program_version=job.source_program_version,
        method=job.method_detail,
        energy_hartree=(
            job.reference_energy_hartree
            if job.reference_energy_hartree is not None
            else data.metadata.energy_hartree
        ),
        terminated_normally=job.terminated_normally,
    )
    molecule = Molecule(
        atoms=atoms,
        charge=charge,
        multiplicity=multiplicity,
        metadata=metadata,
        provenance=data.provenance,
        bonds=bonds,
    )
    return CalculationData(molecule=molecule, records={"excited_states": collection})


def attach_excited_states(
    data: CalculationData | OpenWFNData,
    collection: ExcitedStateCollection,
) -> CalculationData | OpenWFNData:
    """Attach excited states while preserving all existing wavefunction objects."""

    if isinstance(data, OpenWFNData):
        calculation = data.calculation
        if calculation is None:
            calculation = _minimal_calculation(data, collection)
        else:
            calculation = replace(
                calculation,
                records={**calculation.records, "excited_states": collection},
            )
        return replace(data, calculation=calculation)

    return replace(data, records={**data.records, "excited_states": collection})
