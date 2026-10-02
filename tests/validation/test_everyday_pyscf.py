"""Optional freshly computed molecular references; never self-generated goldens."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2]/'scripts/validate_everyday_pyscf.py'
spec = importlib.util.spec_from_file_location('everyday_pyscf_validation', SCRIPT)
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


@pytest.mark.parametrize('case', reference.CASES, ids=[case[0] for case in reference.CASES])
def test_molecular_reference(case, tmp_path):
    for dependency in ('pyscf', 'iodata', 'cclib'):
        pytest.importorskip(dependency)
    report = reference.validate_case(case, tmp_path)
    assert report['status'] == 'passed'
    assert report['scf_converged']
    assert report['mayer_max_error'] < 2e-7
    assert report['input_sha256']
