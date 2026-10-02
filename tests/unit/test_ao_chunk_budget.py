from dataclasses import replace
from pathlib import Path

import pytest

from openwfn.parsers.gaussian.fchk import parse_fchk


def test_chunk_budget_accounts_for_long_contractions():
    from openwfn.analysis.basis import bounded_ao_chunk_size

    source = Path(__file__).resolve().parents[2]/'examples/water/water.fchk'
    basis = parse_fchk(source).basis
    ordinary = bounded_ao_chunk_size(basis, 65536)
    shell = replace(basis.shells[0], exponents=(1.,)*1024, coefficients=(.1,)*1024)
    long_basis = replace(basis, shells=(shell, *basis.shells[1:]))
    assert 0 < bounded_ao_chunk_size(long_basis, 65536) < ordinary
    assert bounded_ao_chunk_size(basis, 10) == 10
    with pytest.raises(ValueError, match='positive integer'):
        bounded_ao_chunk_size(basis, 0)
