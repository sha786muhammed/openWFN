"""Helpers for attaching typed excited-state records without copying scientific arrays."""

from dataclasses import replace

from ...data import OpenWFNData
from ...excited_states import ExcitedStateCollection
from ...model import CalculationData


def attach_excited_states(
    data: CalculationData | OpenWFNData,
    collection: ExcitedStateCollection,
) -> CalculationData | OpenWFNData:
    """Attach excited states while preserving all existing wavefunction objects."""

    if isinstance(data, OpenWFNData):
        if data.calculation is None:
            raise ValueError(
                "Cannot attach excited-state records without a molecular CalculationData object."
            )
        calculation = replace(
            data.calculation,
            records={**data.calculation.records, "excited_states": collection},
        )
        return replace(data, calculation=calculation)

    return replace(data, records={**data.records, "excited_states": collection})
