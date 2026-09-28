import pytest

from openwfn.model import Atom, DensityMatrix


def test_atom_preserves_effective_nuclear_charge() -> None:
    atom = Atom(14, (0.0, 0.0, 0.0), nuclear_charge=4.0)

    assert atom.atomic_number == 14
    assert atom.nuclear_charge == pytest.approx(4.0)


def test_density_matrix_preserves_source_label() -> None:
    matrix = DensityMatrix(((1.0,),), "total", source="scf")

    assert matrix.source == "scf"
