from pathlib import Path

import numpy as np
import pytest

from openwfn.analysis.atom_quadrature import AtomQuadratureSettings, iter_atom_centered_chunks
from openwfn.analysis.density import evaluate_density
from openwfn.ingest import load_input

ROOT = Path(__file__).resolve().parents[2]


def _integrated_electrons(path: Path, settings: AtomQuadratureSettings) -> float:
    normalized = load_input(path)
    calculation = normalized.calculation
    assert calculation is not None
    assert calculation.basis is not None
    assert calculation.total_density is not None

    total = 0.0
    for chunk in iter_atom_centered_chunks(calculation.molecule, settings):
        density = evaluate_density(
            calculation.molecule,
            calculation.basis,
            calculation.total_density,
            chunk.points_bohr,
        )
        total += float(np.dot(density, chunk.integration_weights))
    return total


@pytest.mark.parametrize(
    "relative_path",
    [
        "examples/water/water.fchk",
        "examples/methane/methane.fchk",
        "examples/ammonia/ammonia.fchk",
    ],
)
def test_default_atom_quadrature_converges_total_density(relative_path: str) -> None:
    standard = AtomQuadratureSettings()
    fine = AtomQuadratureSettings(
        radial_points=144,
        theta_points=24,
        phi_points=48,
        radial_extent_bohr=24.0,
        chunk_size=65_536,
    )

    standard_electrons = _integrated_electrons(ROOT / relative_path, standard)
    fine_electrons = _integrated_electrons(ROOT / relative_path, fine)

    assert abs(fine_electrons - 10.0) <= 2.0e-3
    assert abs(standard_electrons - 10.0) <= 5.0e-3
    assert abs(standard_electrons - fine_electrons) <= 4.0e-3
