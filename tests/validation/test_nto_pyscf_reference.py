"""Independent PySCF TDA comparisons for the conservative real NTO SVD."""

from __future__ import annotations

import numpy as np
import pytest

from openwfn.analysis.nto import compute_nto_svd

CASES = (
    (
        "water",
        """
O   0.0000   0.0000   0.0000
H   0.7586   0.0000   0.5043
H  -0.7586   0.0000   0.5043
""",
    ),
    (
        "formaldehyde",
        """
C   0.0000   0.0000   0.0000
O   0.0000   0.0000   1.2100
H   0.9400   0.0000  -0.5400
H  -0.9400   0.0000  -0.5400
""",
    ),
    (
        "ethylene",
        """
C  -0.6695   0.0000   0.0000
C   0.6695   0.0000   0.0000
H  -1.2321   0.9289   0.0000
H  -1.2321  -0.9289   0.0000
H   1.2321   0.9289   0.0000
H   1.2321  -0.9289   0.0000
""",
    ),
)


@pytest.mark.parametrize(("name", "geometry"), CASES, ids=[case[0] for case in CASES])
def test_nto_weights_match_pyscf_tda(name: str, geometry: str) -> None:
    pyscf = pytest.importorskip("pyscf")
    from pyscf import gto, scf, tdscf

    molecule = gto.M(
        atom=geometry,
        basis="sto-3g",
        unit="Angstrom",
        charge=0,
        spin=0,
        symmetry=False,
        verbose=0,
    )
    mean_field = scf.RHF(molecule)
    mean_field.conv_tol = 1e-11
    mean_field.kernel()
    assert mean_field.converged, name

    tda = tdscf.TDA(mean_field)
    tda.nstates = 1
    tda.kernel()
    assert bool(np.asarray(tda.converged).reshape(-1)[0]), name

    excitation = np.asarray(tda.xy[0][0], dtype=float).copy()
    excitation /= np.linalg.norm(excitation)
    actual = compute_nto_svd(excitation)

    reference_weights, _ = tda.get_nto(state=1)
    reference_weights = np.asarray(reference_weights, dtype=float)
    np.testing.assert_allclose(
        actual.weights,
        reference_weights[: len(actual.weights)],
        rtol=2e-11,
        atol=2e-12,
    )
    assert actual.transition_norm == pytest.approx(1.0, abs=2e-12)
    assert pyscf.__version__
