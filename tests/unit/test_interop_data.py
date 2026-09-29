from pathlib import Path

import pytest

import openwfn
from openwfn.data import (
    INTEROP_SCHEMA_VERSION,
    IntegralData,
    IntegralTerm,
    OpenWFNData,
    PeriodicData,
    SourceMetadata,
    StructureData,
    wrap_calculation,
)
from openwfn.errors import DataUnavailableError
from openwfn.parsers.gaussian.fchk import parse_fchk

ROOT = Path(__file__).resolve().parents[2]
WATER_FCHK = ROOT / "examples" / "water" / "water.fchk"


def test_structure_data_validates_parallel_atom_fields() -> None:
    structure = StructureData(
        coordinates=((0.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        atomic_numbers=(8, 1),
        labels=("O", "H"),
        charge=0,
        multiplicity=1,
    )

    assert structure.atomic_numbers == (8, 1)
    assert structure.labels == ("O", "H")

    with pytest.raises(ValueError, match="atomic_numbers"):
        StructureData(
            coordinates=((0.0, 0.0, 0.0),),
            atomic_numbers=(8, 1),
        )


def test_structure_data_allows_unknown_atomic_numbers_but_not_invalid_coordinates() -> None:
    structure = StructureData(
        coordinates=((0.0, 0.0, 0.0),),
        atomic_numbers=(None,),
        labels=("X",),
    )
    assert structure.atomic_numbers == (None,)

    with pytest.raises(ValueError, match="three values"):
        StructureData(coordinates=((0.0, 0.0),), atomic_numbers=(1,))  # type: ignore[arg-type]


def test_periodic_data_requires_three_finite_cell_vectors() -> None:
    periodic = PeriodicData(
        cell_vectors=((10.0, 0.0, 0.0), (0.0, 10.0, 0.0), (0.0, 0.0, 10.0)),
        periodic_axes=(True, True, False),
    )
    assert periodic.periodic_axes == (True, True, False)

    with pytest.raises(ValueError, match="three cell vectors"):
        PeriodicData(cell_vectors=((1.0, 0.0, 0.0),))  # type: ignore[arg-type]


def test_integral_and_source_metadata_are_typed_and_finite() -> None:
    integrals = IntegralData(
        n_orbitals=2,
        n_electrons=2,
        core_energy_hartree=-1.0,
        one_electron=(IntegralTerm((0, 1), -0.25),),
        two_electron=(IntegralTerm((0, 0, 1, 1), 0.5),),
    )
    metadata = SourceMetadata(source_program="ExampleQC", energy_hartree=-75.0)

    assert integrals.one_electron[0].indices == (0, 1)
    assert metadata.energy_hartree == -75.0

    with pytest.raises(ValueError, match="non-negative"):
        IntegralData(n_orbitals=-1)


def test_wrap_calculation_preserves_molecular_objects_and_provenance() -> None:
    calculation = parse_fchk(WATER_FCHK)
    wrapped = wrap_calculation(calculation)

    assert isinstance(wrapped, OpenWFNData)
    assert wrapped.calculation is calculation
    assert wrapped.molecule is calculation.molecule
    assert wrapped.basis is calculation.basis
    assert wrapped.alpha_orbitals is calculation.alpha_orbitals
    assert wrapped.total_density is calculation.total_density
    assert wrapped.provenance is calculation.molecule.provenance
    assert wrapped.structure is not None
    assert wrapped.structure.atomic_numbers == tuple(
        atom.atomic_number for atom in calculation.molecule.atoms
    )
    assert wrapped.structure.coordinates == tuple(
        atom.coordinates for atom in calculation.molecule.atoms
    )


def test_non_molecular_container_has_nullable_wavefunction_fields_and_no_molecule() -> None:
    calculation = parse_fchk(WATER_FCHK)
    provenance = calculation.molecule.provenance
    assert provenance is not None
    data = OpenWFNData(
        calculation=None,
        structure=StructureData(
            coordinates=((0.0, 0.0, 0.0),),
            atomic_numbers=(1,),
        ),
        periodic=None,
        grids=(),
        integrals=None,
        metadata=SourceMetadata(),
        provenance=provenance,
    )

    assert data.basis is None
    assert data.alpha_orbitals is None
    assert data.beta_orbitals is None
    assert data.total_density is None
    assert data.spin_density is None
    with pytest.raises(DataUnavailableError, match="molecular calculation"):
        _ = data.molecule


def test_interop_foundation_is_public_and_versioned() -> None:
    assert INTEROP_SCHEMA_VERSION == "1.0"
    assert openwfn.INTEROP_SCHEMA_VERSION == "1.0"
    assert {
        "INTEROP_SCHEMA_VERSION",
        "OpenWFNData",
        "StructureData",
        "PeriodicData",
        "IntegralData",
    }.issubset(openwfn.__all__)
