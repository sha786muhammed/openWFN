import numpy as np

from openwfn.analysis import nci, realspace
from openwfn.model import (
    Atom,
    BasisSet,
    BasisShell,
    CalculationData,
    CalculationMetadata,
    DensityMatrix,
    Molecule,
)


def _single_s_data(*, method: str | None = None, density_source: str = "total") -> CalculationData:
    molecule = Molecule(
        (Atom(1, (0.0, 0.0, 0.0)),),
        0,
        1,
        CalculationMetadata("fixture", method=method),
    )
    return CalculationData(
        molecule=molecule,
        basis=BasisSet((BasisShell(0, 0, (0.9,), (1.0,)),)),
        total_density=DensityMatrix(((2.0,),), density_source),
        records={"Number of alpha electrons": 1, "Number of beta electrons": 1},
    )


def test_evaluate_nci_matches_shared_density_fields_and_pure_kernel() -> None:
    data = _single_s_data()
    points = np.array(((0.2, 0.1, -0.3), (0.4, -0.2, 0.5)), dtype=float)
    settings = nci.NCISettings()

    fields = realspace.evaluate_density_fields(data, points, kind="total")
    expected = nci.compute_nci_components(
        fields.rho, fields.gradient, fields.hessian, settings=settings
    )
    actual = nci.evaluate_nci(data, points, settings=settings)

    np.testing.assert_allclose(actual.rho, expected.rho)
    np.testing.assert_allclose(actual.gradient_norm, expected.gradient_norm)
    np.testing.assert_allclose(actual.rdg, expected.rdg)
    np.testing.assert_allclose(actual.hessian_eigenvalues, expected.hessian_eigenvalues)
    np.testing.assert_allclose(actual.lambda2, expected.lambda2)
    np.testing.assert_allclose(actual.signed_density, expected.signed_density)
    assert actual.rdg_valid_mask.tolist() == expected.rdg_valid_mask.tolist()
    assert actual.field_valid_mask.tolist() == expected.field_valid_mask.tolist()


def test_evaluate_nci_chunking_matches_single_batch() -> None:
    data = _single_s_data()
    points = np.array(
        ((0.1, 0.2, 0.3), (0.2, -0.3, 0.4), (-0.4, 0.1, 0.2), (0.5, 0.2, -0.1)),
        dtype=float,
    )

    full = nci.evaluate_nci(data, points)
    chunked = nci.evaluate_nci(data, points, chunk_size=2)

    np.testing.assert_allclose(chunked.rho, full.rho)
    np.testing.assert_allclose(chunked.gradient_norm, full.gradient_norm)
    np.testing.assert_allclose(chunked.rdg, full.rdg)
    np.testing.assert_allclose(chunked.hessian_eigenvalues, full.hessian_eigenvalues)
    np.testing.assert_allclose(chunked.lambda2, full.lambda2)
    np.testing.assert_allclose(chunked.signed_density, full.signed_density)
    assert chunked.rdg_valid_mask.tolist() == full.rdg_valid_mask.tolist()
    assert chunked.field_valid_mask.tolist() == full.field_valid_mask.tolist()


def test_evaluate_nci_empty_points_are_empty() -> None:
    result = nci.evaluate_nci(_single_s_data(), np.empty((0, 3), dtype=float))

    assert result.rho.shape == (0,)
    assert result.gradient_norm.shape == (0,)
    assert result.rdg.shape == (0,)
    assert result.hessian_eigenvalues.shape == (0, 3)
    assert result.lambda2.shape == (0,)
    assert result.signed_density.shape == (0,)
