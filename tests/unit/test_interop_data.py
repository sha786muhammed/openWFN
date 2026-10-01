from pathlib import Path

import pytest

from openwfn.errors import DataUnavailableError
from openwfn.model import Provenance, VolumetricGrid
from openwfn.parsers.gaussian.fchk import parse_fchk

ROOT = Path(__file__).resolve().parents[2]


def _provenance(source_format: str = "test") -> Provenance:
    return Provenance(
        source_path="fixture",
        sha256="0" * 64,
        parser="test",
        source_format=source_format,
    )


def test_wrap_calculation_preserves_existing_fchk_objects() -> None:
    from openwfn.data import wrap_calculation

    existing = parse_fchk(ROOT / "examples" / "water" / "water.fchk")
    wrapped = wrap_calculation(existing)

    assert wrapped.calculation is existing
    assert wrapped.molecule is existing.molecule
    assert wrapped.basis is existing.basis
    assert wrapped.alpha_orbitals is existing.alpha_orbitals
    assert wrapped.total_density is existing.total_density
    assert wrapped.provenance is existing.molecule.provenance
    assert wrapped.structure is not None
    assert wrapped.structure.coordinates == tuple(atom.coordinates for atom in existing.molecule.atoms)


def test_structure_only_accepts_unknown_atomic_numbers() -> None:
    from openwfn.data import OpenWFNData, SourceMetadata, StructureData

    structure = StructureData(
        coordinates=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
        atomic_numbers=(6, None),
        labels=("C", "X"),
    )
    data = OpenWFNData(
        calculation=None,
        structure=structure,
        periodic=None,
        grids=(),
        integrals=None,
        metadata=SourceMetadata(),
        provenance=_provenance("xyz"),
    )

    assert data.structure is structure
    assert data.basis is None
    with pytest.raises(DataUnavailableError, match="molecular calculation"):
        _ = data.molecule


def test_periodic_input_does_not_fabricate_molecule() -> None:
    from openwfn.data import OpenWFNData, PeriodicData, SourceMetadata, StructureData

    data = OpenWFNData(
        calculation=None,
        structure=StructureData(coordinates=((0.0, 0.0, 0.0),), atomic_numbers=(14,)),
        periodic=PeriodicData(
            cell_vectors=((5.0, 0.0, 0.0), (0.0, 5.0, 0.0), (0.0, 0.0, 5.0))
        ),
        grids=(),
        integrals=None,
        metadata=SourceMetadata(),
        provenance=_provenance("poscar"),
    )

    assert data.periodic is not None
    assert data.calculation is None
    with pytest.raises(DataUnavailableError):
        _ = data.molecule


def test_grid_only_input_is_representable_without_calculation() -> None:
    from openwfn.data import OpenWFNData, SourceMetadata

    grid = VolumetricGrid(
        origin=(0.0, 0.0, 0.0),
        axes=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        shape=(1, 1, 1),
        values=(0.5,),
        value_unit="electron/angstrom^3",
    )
    data = OpenWFNData(
        calculation=None,
        structure=None,
        periodic=None,
        grids=(grid,),
        integrals=None,
        metadata=SourceMetadata(),
        provenance=_provenance("cube"),
    )

    assert data.grids == (grid,)
    assert data.total_density is None


def test_integral_only_input_preserves_sparse_terms() -> None:
    from openwfn.data import IntegralData, IntegralTerm, OpenWFNData, SourceMetadata

    integrals = IntegralData(
        n_orbitals=2,
        n_electrons=2,
        core_energy_hartree=0.25,
        one_electron=(IntegralTerm((0, 1), -0.5),),
        two_electron=(IntegralTerm((0, 0, 1, 1), 0.125),),
    )
    data = OpenWFNData(
        calculation=None,
        structure=None,
        periodic=None,
        grids=(),
        integrals=integrals,
        metadata=SourceMetadata(),
        provenance=_provenance("fcidump"),
    )

    assert data.integrals is integrals
    assert data.alpha_orbitals is None


def test_structure_and_periodic_values_must_be_finite_and_shape_consistent() -> None:
    from openwfn.data import PeriodicData, StructureData

    with pytest.raises(ValueError, match="same number"):
        StructureData(coordinates=((0.0, 0.0, 0.0),), atomic_numbers=(1, 1))
    with pytest.raises(ValueError, match="finite"):
        StructureData(coordinates=((float("nan"), 0.0, 0.0),), atomic_numbers=(1,))
    with pytest.raises(ValueError, match="finite"):
        PeriodicData(
            cell_vectors=((float("inf"), 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
        )


def test_structure_effective_charges_are_validated_and_classified() -> None:
    from openwfn.data import StructureData

    structure = StructureData(
        coordinates=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 0.0, 0.0)),
        atomic_numbers=(8, 8, 14),
        effective_nuclear_charges=(8.0, 0.0, 4.0),
    )
    assert structure.effective_nuclear_charges == (8.0, 0.0, 4.0)

    for charges, pattern in (
        ((8.0,), "same number"),
        ((8.0, float("nan"), 4.0), "finite"),
        ((8.0, -1.0, 4.0), "non-negative"),
    ):
        with pytest.raises(ValueError, match=pattern):
            StructureData(
                coordinates=structure.coordinates,
                atomic_numbers=structure.atomic_numbers,
                effective_nuclear_charges=charges,
            )


def test_native_ghost_and_ecp_charges_survive_wrapping() -> None:
    from openwfn.data import wrap_calculation

    scientific = ROOT / "tests" / "fixtures" / "scientific"
    ghost = wrap_calculation(parse_fchk(scientific / "ghost_minimal.fchk"))
    ecp = wrap_calculation(parse_fchk(scientific / "ecp_minimal.fchk"))

    assert ghost.structure is not None
    assert ecp.structure is not None
    assert ghost.structure.effective_nuclear_charges[1] == 0.0
    assert ecp.structure.effective_nuclear_charges[0] == 4.0
