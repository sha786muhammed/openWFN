import json
import re
from pathlib import Path

import pytest

from openwfn.cli import main
from openwfn.ingest import load_input
from openwfn.reporting import build_report_record


def test_report_preserves_unknown_xyz_electronic_state(tmp_path):
    source = tmp_path / 'atom.xyz'
    source.write_text('1\natom\nHe 0 0 0\n')
    output = tmp_path / 'report.html'
    assert main([str(source), 'report', 'build', str(output), '--analyses', 'summary']) == 0
    text = output.read_text()
    match = re.search(r'<script[^>]+type="application/json"[^>]*>(.*?)</script>', text, re.S)
    assert match
    manifest = json.loads(match.group(1))
    summary = manifest['sections'][0]['data']
    assert summary['charge'] is None
    assert summary['multiplicity'] is None
    assert manifest['sections'][0]['result_status'] == 'partial'


def test_report_record_preserves_source_provenance(tmp_path):
    source = tmp_path / 'atom.xyz'
    source.write_text('1\natom\nHe 0 0 0\n')
    record = build_report_record(load_input(source), ('summary',), tmp_path / 'report.html', 'html', 'test')
    assert record.provenance['source_path'] == str(source)
    assert record.provenance['input_sha256']


def test_report_rejects_input_alias_even_with_overwrite(tmp_path):
    source = tmp_path / 'source.html'
    original = '1\natom\nHe 0 0 0\n'
    source.write_text(original)
    data = load_input(source, format_hint='xyz')
    with pytest.raises(ValueError, match='input'):
        build_report_record(data, ('summary',), source, 'html', 'test', overwrite=True)
    assert source.read_text() == original


def test_failed_report_write_preserves_existing_output(tmp_path, monkeypatch):
    source = tmp_path / 'atom.xyz'
    source.write_text('1\natom\nHe 0 0 0\n')
    output = tmp_path / 'report.html'
    output.write_text('keep')
    original_write = Path.write_text

    def fail_write(path, text, **kwargs):
        original_write(path, 'partial', **kwargs)
        raise OSError('disk full')

    monkeypatch.setattr(Path, 'write_text', fail_write)
    with pytest.raises(OSError, match='disk full'):
        build_report_record(load_input(source), ('summary',), output, 'html', 'test', overwrite=True)
    assert output.read_text() == 'keep'
