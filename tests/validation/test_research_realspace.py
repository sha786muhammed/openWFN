from pathlib import Path

import pytest


@pytest.mark.parametrize('name', ['hydrogen', 'ethylene', 'biphenyl'])
def test_research_realspace_matches_pyscf_fields_and_independent_stationary_point(name, tmp_path):
    pytest.importorskip('pyscf')
    pytest.importorskip('iodata')
    from scripts.validate_research_realspace import validate_case

    report = validate_case(name, tmp_path)
    assert report['checks_passed'] is True
    assert report['critical_point']['label'] == '(3,-1)'
    assert report['critical_point']['position_max_error_bohr'] < 2e-5
    assert report['critical_point']['density_abs_error'] < 1e-7
    assert report['records']['qtaim']['status'] == 'partial'
    assert report['records']['qtaim']['data']['search_complete'] is False
    assert report['records']['qtaim']['warnings']
    assert len(report['input_sha256']) == 64
    assert (tmp_path / f'{name}.molden').is_file()
    assert report['atom_count'] == {'hydrogen': 2, 'ethylene': 6, 'biphenyl': 22}[name]


def test_realspace_reference_run_preserves_existing_inputs(tmp_path):
    from scripts.validate_research_realspace import validate_case

    source = Path(tmp_path / 'hydrogen.molden')
    source.write_bytes(b'keep this input')
    with pytest.raises(FileExistsError):
        validate_case('hydrogen', tmp_path)
    assert source.read_bytes() == b'keep this input'
