"""Fresh native charges against captured external results, not a new external run."""

import json
from hashlib import sha256
from pathlib import Path

import numpy as np
import pytest

from openwfn import load

ROOT = Path(__file__).resolve().parents[2]
REPORT = json.loads((ROOT / 'validation/hirshfeld/reference-report.json').read_text())


@pytest.mark.parametrize('case', REPORT['cases'], ids=[case['id'] for case in REPORT['cases']])
def test_current_hirshfeld_matches_captured_external_charges(case):
    pytest.importorskip('iodata')
    source = ROOT / case['input_path']
    assert sha256(source.read_bytes()).hexdigest() == case['input_sha256']
    result = load(source).hirshfeld()
    assert result.status == 'success', result.warnings
    charges = [atom['charge'] for atom in result.data['atoms']]
    np.testing.assert_allclose(charges, case['external_charges_e'], rtol=0, atol=1e-3)
    assert result.data['reference_library']['sha256'] == REPORT['reference_library']['sha256']
    assert abs(sum(charges) - case['molecular_charge']) <= 5e-3
