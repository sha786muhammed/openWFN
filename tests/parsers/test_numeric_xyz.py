import pytest

from openwfn.api import load
from openwfn.errors import ParseError


def test_numeric_xyz_atom_labels_preserve_elements_without_inventing_charge(tmp_path):
    source = tmp_path / 'numeric.xyz'
    source.write_text('3\nwater\n1 .783837 -.492236 0\n8 0 .062020 0\n1 -.783837 -.492236 0\n')
    calculation = load(source)
    assert calculation.data.structure.atomic_numbers == (1, 8, 1)
    assert calculation.data.structure.charge is None
    assert calculation.data.structure.multiplicity is None
    assert calculation.analyze('summary').data['formula'] == 'H2O'


@pytest.mark.parametrize('label', ['0', '-1', '119'])
def test_numeric_xyz_rejects_unmapped_nuclei_instead_of_guessing_ghosts(label, tmp_path):
    source = tmp_path / 'invalid.xyz'
    source.write_text(f'1\ninvalid\n{label} 0 0 0\n')
    with pytest.raises(ParseError):
        load(source)
