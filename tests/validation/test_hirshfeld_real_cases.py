from pathlib import Path

import pytest

from openwfn.analysis.hirshfeld import hirshfeld_population
from openwfn.ingest import load_input

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("relative_path", "expected_electrons", "expected_charge"),
    [
        ("examples/water/water.fchk", 10.0, 0.0),
        ("examples/methane/methane.fchk", 10.0, 0.0),
        ("examples/ammonia/ammonia.fchk", 10.0, 0.0),
    ],
)
def test_native_hirshfeld_real_wavefunctions_close_without_charge_rescaling(
    relative_path: str,
    expected_electrons: float,
    expected_charge: float,
) -> None:
    normalized = load_input(ROOT / relative_path)
    assert normalized.calculation is not None

    result = hirshfeld_population(normalized.calculation)

    assert result.diagnostics.expected_electrons == pytest.approx(expected_electrons)
    assert result.diagnostics.expected_molecular_charge == pytest.approx(expected_charge)
    assert result.diagnostics.electron_count_residual <= 5.0e-3
    assert result.diagnostics.population_partition_residual <= 1.0e-8
    assert result.diagnostics.charge_closure_residual <= 5.0e-3
    assert result.diagnostics.unresolved_promolecule_points == 0
    assert result.result_status == "success"


def test_methane_symmetry_is_preserved_by_native_hirshfeld_integration() -> None:
    normalized = load_input(ROOT / "examples/methane/methane.fchk")
    assert normalized.calculation is not None

    result = hirshfeld_population(normalized.calculation)
    hydrogen_charges = [atom.net_charge for atom in result.atoms if atom.symbol == "H"]

    assert len(hydrogen_charges) == 4
    assert max(hydrogen_charges) - min(hydrogen_charges) <= 5.0e-3
