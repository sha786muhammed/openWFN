import numpy as np
import pytest

from openwfn.analysis.qtaim import QTAIMSettings, classify_qtaim_hessian, topology_relation


@pytest.mark.parametrize(
    ("diagonal", "signature", "label"),
    [
        ((-3.0, -2.0, -1.0), -3, "(3,-3)"),
        ((-3.0, -2.0, 1.0), -1, "(3,-1)"),
        ((-3.0, 2.0, 1.0), 1, "(3,+1)"),
        ((3.0, 2.0, 1.0), 3, "(3,+3)"),
    ],
)
def test_qtaim_hessian_classifies_standard_rank_signature_types(
    diagonal: tuple[float, float, float], signature: int, label: str
) -> None:
    result = classify_qtaim_hessian(np.diag(diagonal), curvature_tolerance=1.0e-8)

    assert result.rank == 3
    assert result.signature == signature
    assert result.label == label
    assert result.eigenvalues == tuple(sorted(diagonal))


def test_qtaim_hessian_symmetrizes_and_rejects_near_degenerate_curvature() -> None:
    hessian = np.array(
        [
            [-2.0, 0.2, 0.0],
            [0.0, -1.0, 0.0],
            [0.0, 0.0, 1.0e-10],
        ],
        dtype=float,
    )

    result = classify_qtaim_hessian(hessian, curvature_tolerance=1.0e-8)

    assert result.rank == 2
    assert result.signature is None
    assert result.label is None
    assert all(np.isfinite(result.eigenvalues))


def test_qtaim_hessian_rejects_nonfinite_or_wrong_shape_input() -> None:
    with pytest.raises(ValueError, match="shape"):
        classify_qtaim_hessian(np.eye(2), curvature_tolerance=1.0e-8)
    with pytest.raises(ValueError, match="finite"):
        classify_qtaim_hessian(
            np.array(((1.0, 0.0, 0.0), (0.0, np.nan, 0.0), (0.0, 0.0, -1.0))),
            curvature_tolerance=1.0e-8,
        )


def test_qtaim_settings_validate_finite_positive_limits() -> None:
    settings = QTAIMSettings()

    assert settings.max_iterations > 0
    assert settings.max_seeds > 0
    assert settings.max_path_steps > 0

    with pytest.raises(ValueError, match="gradient_tolerance"):
        QTAIMSettings(gradient_tolerance=0.0)
    with pytest.raises(ValueError, match="max_iterations"):
        QTAIMSettings(max_iterations=0)


def test_qtaim_topology_relation_uses_finite_molecule_poincare_hopf_count() -> None:
    assert topology_relation({"(3,-3)": 3, "(3,-1)": 2, "(3,+1)": 0, "(3,+3)": 0}) == 1
    assert topology_relation({"(3,-3)": 6, "(3,-1)": 6, "(3,+1)": 1, "(3,+3)": 0}) == 1
    assert topology_relation({"(3,-3)": 1, "(3,-1)": 2, "(3,+1)": 0, "(3,+3)": 0}) == -1
