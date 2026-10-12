from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def reviewer():
    try:
        from scripts.review_workflows import review_file
    except ImportError:
        pytest.fail('The reproducible property coverage runner is missing')
    return review_file


def test_structure_records_unavailable_properties_without_claiming_validation():
    report = reviewer()(ROOT / 'examples/ammonia/ammonia.xyz')
    rows = {row['analysis']: row for row in report['analyses']}
    assert rows['summary']['outcome'] == 'partial'
    assert rows['summary']['record']['data']['formula'] == 'H3N'
    assert rows['frontier']['outcome'] == 'unavailable'
    assert rows['ir-spectrum']['outcome'] == 'unavailable'
    assert rows['ir-spectrum']['missing_requirements']
    assert rows['density-integrate']['outcome'] == 'unavailable'
    assert report['independent_validation'] is False
    assert len(report['input_sha256']) == 64


def test_molden_review_runs_point_fields_and_retains_units():
    report = reviewer()(ROOT / 'examples/everyday-qc/ethanol.molden')
    rows = {row['analysis']: row for row in report['analyses']}
    assert rows['frontier-all']['outcome'] == 'calculated'
    assert rows['mulliken']['record']['data']['electron_count'] == pytest.approx(26)
    assert rows['density-derivatives']['outcome'] == 'calculated'
    assert rows['density-derivatives']['record']['units']['rho'] == 'electron/bohr^3'
    assert len(rows['density-derivatives']['record']['data']['rho']) == 2
    assert rows['ir-spectrum']['outcome'] == 'unavailable'
    assert rows['density-integrate']['record']['data']['spacing'] == .4
    assert report['parameters']['qtaim']['include_bond_paths'] is False


def test_broken_file_is_a_load_failure_not_missing_scientific_data(tmp_path):
    source = tmp_path / 'broken.fchk'
    source.write_text('not a formatted checkpoint', encoding='utf-8')
    report = reviewer()(source)
    assert report['load_status'] == 'failed'
    assert report['error']
    assert report['analyses'] == []


def test_open_shell_localization_uses_explicit_spin_channel():
    report = reviewer()(ROOT / 'examples/everyday-qc/oxygen_triplet.molden')
    rows = {row['analysis']: row for row in report['analyses']}
    assert rows['elf']['outcome'] == 'calculated'
    assert rows['lol']['outcome'] == 'calculated'
    assert report['parameters']['elf']['channel'] == 'alpha'
    assert report['parameters']['lol']['channel'] == 'alpha'


def test_unimplemented_hirshfeld_reference_is_not_a_corrupt_file():
    report = reviewer()(ROOT / 'tests/fixtures/interop/cp2klog/helium.cp2k.out',
                        format_hint='cp2klog')
    rows = {row['analysis']: row for row in report['analyses']}
    assert rows['hirshfeld']['outcome'] == 'unsupported-scope'
    assert 'reference element' in rows['hirshfeld']['record']['error']['message']


def test_upstream_corpus_selection_keeps_ghost_ecp_large_and_negative_cases():
    from scripts import review_workflows
    assert hasattr(review_workflows, 'iodata_corpus'), 'Upstream corpus selection is missing'
    names = {path.name for path, hint in review_workflows.iodata_corpus()}
    assert {'water_dimer_ghost.fchk', 'monosilicic_acid_hf_lan.fchk',
            'cah110_hf_sto3g_g09.wfx', 'water_wrong_spinmult.mkl',
            'orca_gradient.out'} <= names
