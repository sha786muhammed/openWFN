"""Integrity of captured real browser evidence; scientific field status stays separate."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_captured_browser_scope_and_input_integrity():
    report = json.loads((ROOT/'validation/everyday-qc/browser-report.json').read_text())
    assert report['status'] == 'passed'
    assert len(report['cases']) == 11
    assert sum(len(case['measurements']) for case in report['cases']) == 21
    for case in report['cases']:
        source = ROOT/f"examples/everyday-qc/{case['case']}.molden"
        assert hashlib.sha256(source.read_bytes()).hexdigest() == case['input_sha256']
        assert case['status'] == 'passed'
        assert case['workspaces'] == 5
        assert not case['javascript_errors']
        assert not case['network_requests']
        assert all(measure['absolute_error'] <= 1e-6 for measure in case['measurements'])
        density = next(field for field in case['fields'] if field['id'] == 'density-total')
        assert density['status'] == 'partial'
        assert density['validation_status'] == 'Experimental'
        assert density['warnings']
