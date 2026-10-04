import numpy as np
import pytest

import openwfn.analysis.limits as limits
import openwfn.analysis.realspace as realspace
from openwfn.model import (
    Atom,
    BasisSet,
    BasisShell,
    CalculationData,
    CalculationMetadata,
    DensityMatrix,
    Molecule,
)


def _single_s_data() -> CalculationData:
    molecule = Molecule(
        (Atom(1, (0.0, 0.0, 0.0)),),
        0,
        1,
        CalculationMetadata("fixture"),
    )
    return CalculationData(
        molecule=molecule,
        basis=BasisSet((BasisShell(0, 0, (1.0,), (1.0,)),)),
        total_density=DensityMatrix(((1.0,),), "total"),
    )


def test_existing_grid_and_quadrature_ceilings_are_centralized_without_value_changes() -> None:
    assert limits.MAX_GRID_POINTS == 2_000_000
    assert limits.MAX_ATOM_QUADRATURE_POINTS == 20_000_000
    assert limits.MAX_POINT_ANALYSIS_POINTS == 2_000_000
    assert limits.DEFAULT_AO_WORKING_BYTES == 128 * 1024**2


def test_ao_temporary_memory_estimator_uses_point_ao_component_product() -> None:
    assert limits.estimate_ao_temporary_bytes(17, 23, 13) == 17 * 23 * 13 * 8
    assert limits.estimate_ao_temporary_bytes(17, 23, 4) == 17 * 23 * 4 * 8


@pytest.mark.parametrize(
    ("point_count", "nao", "components", "message"),
    (
        (-1, 10, 13, "point_count"),
        (1, 0, 13, "nao"),
        (1, 10, 0, "requested_components"),
    ),
)
def test_ao_temporary_memory_estimator_rejects_invalid_dimensions(
    point_count: int,
    nao: int,
    components: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        limits.estimate_ao_temporary_bytes(point_count, nao, components)


def test_point_analysis_limit_error_reports_requested_amount_and_ceiling() -> None:
    with pytest.raises(ValueError, match=r"2,000,001.*2,000,000"):
        limits.validate_point_analysis_request(2_000_001)


def test_memory_bounded_chunk_size_uses_requested_components() -> None:
    bytes_for_three_points = 3 * 10 * 13 * 8

    assert (
        limits.bounded_point_chunk_size(
            point_count=100,
            nao=10,
            requested_components=13,
            requested_chunk_size=100,
            working_bytes=bytes_for_three_points,
        )
        == 3
    )


def test_memory_limit_error_reports_one_point_request_and_ceiling() -> None:
    with pytest.raises(ValueError, match=r"1,040.*1,000"):
        limits.bounded_point_chunk_size(
            point_count=1,
            nao=10,
            requested_components=13,
            requested_chunk_size=1,
            working_bytes=1_000,
        )


def test_density_point_ceiling_is_checked_before_ao_evaluation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(limits, "MAX_POINT_ANALYSIS_POINTS", 2)

    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("AO evaluator must not run for an over-limit point request")

    monkeypatch.setattr(realspace, "evaluate_ao_fields", fail_if_called)

    with pytest.raises(ValueError, match=r"3.*2"):
        realspace.evaluate_density_fields(_single_s_data(), np.zeros((3, 3)))


def test_ked_point_ceiling_is_checked_before_ao_evaluation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(limits, "MAX_POINT_ANALYSIS_POINTS", 2)

    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("AO evaluator must not run for an over-limit point request")

    monkeypatch.setattr(realspace, "evaluate_ao_fields", fail_if_called)

    with pytest.raises(ValueError, match=r"3.*2"):
        realspace.evaluate_kinetic_energy_density(_single_s_data(), np.zeros((3, 3)))
