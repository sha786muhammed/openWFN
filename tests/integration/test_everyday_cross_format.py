"""Cross-format regressions with explicit representation and spin conventions."""
from pathlib import Path

import numpy as np
import pytest

from openwfn.api import load

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT/'examples/water/water.fchk'


@pytest.mark.parametrize('fmt', ['molden', 'mwfn', 'wfn', 'wfx'])
def test_mayer_equivalent_water_preserves_source_spin(fmt):
    pytest.importorskip('iodata')
    reference = load(WATER).mayer()
    converted = load(ROOT/f'tests/fixtures/interop/{fmt}/water.{fmt}').mayer()
    assert converted.status == 'success', converted.error
    assert np.asarray(converted.data['bond_order_matrix']) == pytest.approx(np.asarray(reference.data['bond_order_matrix']), abs=2e-7)


@pytest.mark.parametrize('fmt', ['molden', 'mwfn'])
def test_composition_same_contracted_basis(fmt):
    pytest.importorskip('iodata')
    reference = load(WATER).orbital_composition(mo=2)
    converted = load(ROOT/f'tests/fixtures/interop/{fmt}/water.{fmt}').orbital_composition(mo=2)
    a = [row['fraction'] for row in reference.data['atom_contributions']]
    b = [row['fraction'] for row in converted.data['atom_contributions']]
    assert a == pytest.approx(b, abs=2e-7)


@pytest.mark.parametrize('name', ['lih_cation_rohf.wfx', 'lih_cation_uhf.wfx'])
def test_source_open_shell_spin_survives_iodata_adapter(name):
    iodata = pytest.importorskip('iodata')
    source = Path(iodata.__file__).parent/'test/data'/name
    if not source.exists():
        pytest.skip('IOData reference corpus not packaged')
    raw = iodata.load_one(str(source))
    calc = load(source).data.calculation
    assert calc.spin_density is not None
    assert np.max(np.abs(np.asarray(calc.spin_density.values))) > .01
    assert load(source).mayer().status == 'success'
    from openwfn.analysis.basis import overlap_matrix
    trace_spin = np.trace(np.asarray(calc.spin_density.values) @ overlap_matrix(calc.basis, calc.molecule))
    assert trace_spin == pytest.approx(raw.mo.occsa.sum()-raw.mo.occsb.sum(), abs=2e-7)
