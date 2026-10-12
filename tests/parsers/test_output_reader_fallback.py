from pathlib import Path

import pytest

from openwfn.api import load
from openwfn.errors import ParseError


def test_output_fallback_keeps_real_vibrations_without_fabricating_wavefunction(monkeypatch):
    iodata = pytest.importorskip('iodata')
    source = Path(iodata.__file__).parent / 'test/data/water_hf_ccpvtz_freq_qchem.out'
    if not source.is_file():
        pytest.skip('Installed IOData test corpus is absent')
    def primary_failure(*args, **kwargs):
        raise ParseError('Primary reader does not recognize this output layout')
    monkeypatch.setattr('openwfn.adapters.iodata.load_iodata', primary_failure)
    calculation = load(source)
    assert calculation.data.structure.atomic_numbers == (8, 1, 1)
    assert calculation.data.structure.charge == 0
    assert calculation.data.basis is None
    assert calculation.data.alpha_orbitals is None
    assert calculation.data.total_density is None
    modes = calculation.analyze('vibrations')
    assert [row['frequency_cm1'] for row in modes.data['modes']] == [1806.46, 3908.95, 3995.]
    assert modes.provenance['input_sha256'] == 'cc69bca032718c3c9982a361eae6a3812ac225d5e070f45110d57bb8312a09ac'
    assert any('cclib' in warning and 'IOData' in warning for warning in modes.warnings)


def test_unreadable_qchem_output_still_fails_cleanly(tmp_path):
    source = tmp_path / 'broken.out'
    source.write_text('Q-Chem\nnot a calculation\n')
    with pytest.raises(ParseError):
        load(source)
