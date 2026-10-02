"""Optional molecular ESP integral comparisons including coarse-grid failures."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2]/'scripts/validate_experimental_esp.py'
spec = importlib.util.spec_from_file_location('experimental_esp_validation', SCRIPT)
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


@pytest.mark.parametrize('name', ['water', 'oh_diffuse_uhf', 'ammonium_cation'])
def test_analytic_molecular_esp(name):
    pytest.importorskip('pyscf')
    pytest.importorskip('iodata')
    result = reference.compare_case(name)
    if name == 'ammonium_cation':
        assert result['status'] == 'partial'
        assert result['history'][-1]['max_absolute_esp_error'] > .005
        assert not result['history'][-1]['conservation_passed']
    else:
        assert result['status'] == 'passed'
        assert result['history'][-1]['max_absolute_esp_error'] < .005
