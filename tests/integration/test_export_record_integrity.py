"""Exports must retain evidence and never publish incomplete serialization."""

import csv
import json
from pathlib import Path

import pytest

from openwfn.exporters.spectra import write_spectrum
from openwfn.exporters.tables import ExportRequest, write_result_table
from openwfn.results import ResultRecord

ROOT = Path(__file__).resolve().parents[2]


def partial_record():
    return ResultRecord(kind='density_integration', analysis_name='density_integration',
        data={'electron_count': 26.42929161, 'expected_electrons': 26.},
        units={'electron_count': 'electron', 'expected_electrons': 'electron'},
        status='partial', validation_status='Experimental',
        warnings=('Electron conservation failed.',),
        provenance={'input_sha256': 'a' * 64, 'source_format': 'molden'})


def test_table_json_retains_full_partial_record(tmp_path):
    record = partial_record()
    path = tmp_path / 'résultats with spaces.json'
    write_result_table(record, ExportRequest(path, 'json'))
    assert json.loads(path.read_text()) == record.as_dict()


def test_failed_analysis_cannot_be_saved_as_an_empty_scientific_csv(tmp_path):
    record = ResultRecord.failure(kind='vibrational_modes', analysis_name='vibrations',
        analysis_version='1', exception=ValueError('Corrupted mode records'), elapsed_seconds=0.)
    path = tmp_path / 'failed.csv'
    with pytest.raises(ValueError, match='failed'):
        write_result_table(record, ExportRequest(path, 'csv'))
    assert not path.exists()
    saved = tmp_path / 'failed.json'
    write_result_table(record, ExportRequest(saved, 'json'))
    assert json.loads(saved.read_text()) == record.as_dict()


def test_table_csv_retains_partial_status_warning_and_source(tmp_path):
    path = tmp_path / 'density.csv'
    write_result_table(partial_record(), ExportRequest(path, 'csv'))
    row = next(csv.DictReader(path.open()))
    assert float(row['electron_count [electron]']) == 26.42929161
    assert row['result_status'] == 'partial'
    assert json.loads(row['warnings']) == ['Electron conservation failed.']
    assert json.loads(row['provenance'])['input_sha256'] == 'a' * 64


@pytest.mark.parametrize('existing', [False, True])
def test_malformed_table_csv_does_not_publish_partial_output(tmp_path, existing):
    path = tmp_path / 'charges.csv'
    if existing:
        path.write_bytes(b'previous complete result')
    record = ResultRecord(kind='hirshfeld_population', data={
        'atoms': [{'atom_index': 1, 'charge': .1}, 'broken record'], 'diagnostics': {}})
    with pytest.raises(ValueError, match='malformed'):
        write_result_table(record, ExportRequest(path, 'csv', overwrite=existing))
    assert path.read_bytes() == b'previous complete result' if existing else not path.exists()
    assert list(tmp_path.iterdir()) == ([path] if existing else [])


@pytest.mark.parametrize('existing', [False, True])
def test_malformed_spectrum_does_not_publish_partial_output(tmp_path, existing):
    path = tmp_path / 'spectrum.csv'
    if existing:
        path.write_bytes(b'previous complete result')
    record = ResultRecord(kind='vibrational_spectrum', data={
        'frequency_cm1': [1000., 2000.], 'intensity': [5.]})
    with pytest.raises(ValueError):
        write_spectrum(record, path, overwrite=existing)
    assert path.read_bytes() == b'previous complete result' if existing else not path.exists()
    assert list(tmp_path.iterdir()) == ([path] if existing else [])


def test_nonfinite_json_is_rejected_without_a_file(tmp_path):
    path = tmp_path / 'bad.json'
    with pytest.raises(ValueError):
        record = ResultRecord(kind='density', data={'value': float('nan')})
        write_result_table(record, ExportRequest(path, 'json'))
    assert not path.exists()


def test_real_ir_exports_keep_exact_curve_values_and_record(tmp_path):
    from openwfn import load

    record = load(ROOT / 'tests/fixtures/gaussian/vibrations/water_freq.log').analyze(
        'ir-spectrum', fwhm_cm1=12., points=321)
    saved = tmp_path / 'ir.json'
    write_spectrum(record, saved)
    assert json.loads(saved.read_text()) == record.as_dict()
    table = tmp_path / 'ir.csv'
    write_spectrum(record, table)
    rows = list(csv.DictReader(table.open()))
    assert len(rows) == 321
    assert [float(row['frequency_cm1']) for row in rows] == record.data['frequency_cm1']
    assert [float(row['intensity']) for row in rows] == record.data['intensity']


def test_report_manifest_keeps_failed_record_without_discarding_evidence(tmp_path):
    from openwfn import load
    from openwfn.analysis.registry import run_analysis_safe
    from openwfn.reporting import build_report

    calc = load(ROOT / 'examples/everyday-qc/ethanol.molden')
    expected = run_analysis_safe(calc.data, 'ir-spectrum').as_dict()
    path = tmp_path / 'missing-ir.html'
    build_report(calc.data, analyses=('ir-spectrum',), output=path, report_format='html',
        command='fixture', parameters={}, generated_at='2026-10-09T00:00:00Z')
    payload = path.read_text().split('<script id="openwfn-report" type="application/json">')[1].split('</script>')[0]
    manifest = json.loads(payload)
    saved = manifest['sections'][0]['record']
    assert set(saved) == set(expected)
    assert saved['elapsed_seconds'] >= 0
    for key in expected.keys() - {'elapsed_seconds'}:
        assert saved[key] == expected[key], key
