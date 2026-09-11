from pathlib import Path

import numpy as np
import pytest

from openwfn.analysis.basis import ao_atom_indices, overlap_matrix
from openwfn.analysis.population import lowdin_population, mulliken_population
from openwfn.parsers.gaussian.fchk import parse_fchk


def test_water_density_overlap_recovers_electron_count() -> None:
    path = Path(__file__).resolve().parents[2] / "examples" / "water" / "water.fchk"
    data = parse_fchk(path)
    assert data.basis is not None
    assert data.total_density is not None
    overlap = overlap_matrix(data.basis, data.molecule)

    np.testing.assert_allclose(overlap, overlap.T, atol=1e-12)
    np.testing.assert_allclose(np.diag(overlap), np.ones(data.basis.n_functions), atol=1e-10)
    mapping = ao_atom_indices(data.basis)
    mulliken = mulliken_population(data.molecule, data.total_density, overlap, mapping)
    lowdin = lowdin_population(data.molecule, data.total_density, overlap, mapping)

    assert mulliken.electron_count == pytest.approx(10.0, abs=1e-6)
    assert lowdin.electron_count == pytest.approx(10.0, abs=1e-6)
    assert sum(mulliken.atomic_charges) == pytest.approx(0.0, abs=1e-6)
    assert sum(lowdin.atomic_charges) == pytest.approx(0.0, abs=1e-6)
