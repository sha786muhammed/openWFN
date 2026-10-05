import numpy as np
import pytest

from openwfn.analysis import localization
from openwfn.model import (
    Atom,
    BasisSet,
    BasisShell,
    CalculationData,
    CalculationMetadata,
    DensityMatrix,
    Molecule,
)


def _molecule() -> Molecule:
    return Molecule(
        (Atom(1, (0.0, 0.0, 0.0)),),
        0,
        1,
        CalculationMetadata("fixture"),
    )


def _restricted_closed_shell() -> CalculationData:
    return CalculationData(
        molecule=_molecule(),
        basis=BasisSet((BasisShell(0, 0, (0.9,), (1.0,)),)),
        total_density=DensityMatrix(((2.0,),), "total"),
        records={"Number of alpha electrons": 1, "Number of beta electrons": 1},
    )


def _open_shell() -> CalculationData:
    return CalculationData(
        molecule=_molecule(),
        basis=BasisSet((BasisShell(0, 0, (0.9,), (1.0,)),)),
        total_density=DensityMatrix(((1.5,),), "total"),
        spin_density=DensityMatrix(((0.5,),), "spin"),
        records={"Number of alpha electrons": 1, "Number of beta electrons": 0},
    )


def test_restricted_closed_shell_total_alpha_beta_elf_are_equal() -> None:
    data = _restricted_closed_shell()
    points = np.array(((0.2, 0.1, -0.3), (0.4, -0.2, 0.5)), dtype=float)

    total = localization.evaluate_elf(data, points, channel="total", chunk_size=1)
    alpha = localization.evaluate_elf(data, points, channel="alpha", chunk_size=1)
    beta = localization.evaluate_elf(data, points, channel="beta", chunk_size=1)

    np.testing.assert_allclose(alpha.values, total.values, atol=1e-13)
    np.testing.assert_allclose(beta.values, total.values, atol=1e-13)
    assert alpha.valid_mask.tolist() == total.valid_mask.tolist()
    assert beta.valid_mask.tolist() == total.valid_mask.tolist()


def test_restricted_closed_shell_total_alpha_beta_lol_are_equal() -> None:
    data = _restricted_closed_shell()
    points = np.array(((0.2, 0.1, -0.3), (0.4, -0.2, 0.5)), dtype=float)

    total = localization.evaluate_lol(data, points, channel="total", chunk_size=1)
    alpha = localization.evaluate_lol(data, points, channel="alpha", chunk_size=1)
    beta = localization.evaluate_lol(data, points, channel="beta", chunk_size=1)

    np.testing.assert_allclose(alpha.values, total.values, atol=1e-13)
    np.testing.assert_allclose(beta.values, total.values, atol=1e-13)


def test_open_shell_total_localization_is_rejected() -> None:
    data = _open_shell()
    points = np.array(((0.2, 0.1, -0.3),), dtype=float)

    with pytest.raises(ValueError, match="restricted closed-shell"):
        localization.evaluate_elf(data, points, channel="total")
    with pytest.raises(ValueError, match="restricted closed-shell"):
        localization.evaluate_lol(data, points, channel="total")


def test_open_shell_alpha_beta_localization_is_supported() -> None:
    data = _open_shell()
    points = np.array(((0.2, 0.1, -0.3), (0.5, 0.2, 0.1)), dtype=float)

    for channel in ("alpha", "beta"):
        elf = localization.evaluate_elf(data, points, channel=channel)
        lol = localization.evaluate_lol(data, points, channel=channel)
        assert elf.valid_mask.tolist() == [True, True]
        assert lol.valid_mask.tolist() == [True, True]
        assert np.all((elf.values >= 0.0) & (elf.values <= 1.0))
        assert np.all((lol.values >= 0.0) & (lol.values <= 1.0))


def test_spin_difference_channel_is_rejected() -> None:
    data = _open_shell()

    with pytest.raises(ValueError, match="total, alpha, or beta"):
        localization.evaluate_elf(data, np.zeros((1, 3)), channel="spin")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="total, alpha, or beta"):
        localization.evaluate_lol(data, np.zeros((1, 3)), channel="spin")  # type: ignore[arg-type]


def test_calculation_localization_chunking_matches_single_batch() -> None:
    data = _restricted_closed_shell()
    points = np.array(
        ((0.1, 0.2, 0.3), (0.2, -0.3, 0.4), (-0.4, 0.1, 0.2), (0.5, 0.2, -0.1)),
        dtype=float,
    )

    elf_full = localization.evaluate_elf(data, points, channel="total")
    elf_chunked = localization.evaluate_elf(data, points, channel="total", chunk_size=2)
    lol_full = localization.evaluate_lol(data, points, channel="total")
    lol_chunked = localization.evaluate_lol(data, points, channel="total", chunk_size=2)

    np.testing.assert_allclose(elf_chunked.values, elf_full.values, rtol=5e-14, atol=5e-15)
    np.testing.assert_allclose(lol_chunked.values, lol_full.values, rtol=5e-14, atol=5e-15)
    np.testing.assert_allclose(elf_chunked.rho, elf_full.rho, rtol=5e-15, atol=5e-16)
    np.testing.assert_allclose(lol_chunked.tau, lol_full.tau, rtol=5e-15, atol=5e-16)


def test_calculation_localization_empty_points_are_empty() -> None:
    data = _restricted_closed_shell()
    points = np.empty((0, 3), dtype=float)

    elf = localization.evaluate_elf(data, points, channel="total")
    lol = localization.evaluate_lol(data, points, channel="total")

    assert elf.values.shape == (0,)
    assert elf.valid_mask.shape == (0,)
    assert lol.values.shape == (0,)
    assert lol.valid_mask.shape == (0,)


def test_density_floor_override_is_applied() -> None:
    data = _restricted_closed_shell()
    points = np.array(((5.0, 0.0, 0.0),), dtype=float)

    elf = localization.evaluate_elf(
        data, points, channel="total", density_floor=1.0e-2
    )
    lol = localization.evaluate_lol(
        data, points, channel="total", density_floor=1.0e-2
    )

    assert elf.valid_mask.tolist() == [False]
    assert lol.valid_mask.tolist() == [False]
    assert elf.invalid_density_count == 1
    assert lol.invalid_density_count == 1
