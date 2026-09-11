from openwfn.analysis.topology import cycle_basis, fragments
from openwfn.model import Atom, Bond, CalculationMetadata, Molecule


def _molecule(atom_count: int, bonds: tuple[Bond, ...]) -> Molecule:
    return Molecule(
        atoms=tuple(Atom(6, (float(index), 0.0, 0.0)) for index in range(atom_count)),
        charge=0,
        multiplicity=1,
        metadata=CalculationMetadata("fixture"),
        bonds=bonds,
    )


def test_fragments_reports_disconnected_components() -> None:
    molecule = _molecule(4, (Bond(0, 1), Bond(2, 3)))

    assert fragments(molecule) == ((0, 1), (2, 3))


def test_cycle_basis_finds_single_six_member_ring() -> None:
    molecule = _molecule(
        6,
        (Bond(0, 1), Bond(1, 2), Bond(2, 3), Bond(3, 4), Bond(4, 5), Bond(0, 5)),
    )

    assert cycle_basis(molecule) == ((0, 1, 2, 3, 4, 5),)
