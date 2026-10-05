"""Noncovalent-interaction fields from density derivatives.

The pointwise numerical kernel in this module is deliberately independent of
file formats, cube export, and presentation.  It follows the total-density NCI
reduced-density-gradient convention and keeps RDG validity separate from
Hessian-dependent lambda2 validity.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DEFAULT_NCI_DENSITY_FLOOR = 1.0e-12
DEFAULT_HESSIAN_ANTISYMMETRY_TOLERANCE = 1.0e-10
DEFAULT_LAMBDA2_AMBIGUITY_ABSOLUTE_TOLERANCE = 1.0e-12
DEFAULT_LAMBDA2_AMBIGUITY_RELATIVE_TOLERANCE = 1.0e-10
_RDG_DENOMINATOR_COEFFICIENT = 2.0 * (3.0 * np.pi**2) ** (1.0 / 3.0)


@dataclass(frozen=True, slots=True)
class NCISettings:
    """Numerical safeguards for pointwise NCI/RDG evaluation."""

    density_floor: float = DEFAULT_NCI_DENSITY_FLOOR
    hessian_antisymmetry_tolerance: float = DEFAULT_HESSIAN_ANTISYMMETRY_TOLERANCE
    lambda2_ambiguity_absolute_tolerance: float = (
        DEFAULT_LAMBDA2_AMBIGUITY_ABSOLUTE_TOLERANCE
    )
    lambda2_ambiguity_relative_tolerance: float = (
        DEFAULT_LAMBDA2_AMBIGUITY_RELATIVE_TOLERANCE
    )

    def __post_init__(self) -> None:
        values = {
            "density_floor": self.density_floor,
            "hessian_antisymmetry_tolerance": self.hessian_antisymmetry_tolerance,
            "lambda2_ambiguity_absolute_tolerance": (
                self.lambda2_ambiguity_absolute_tolerance
            ),
            "lambda2_ambiguity_relative_tolerance": (
                self.lambda2_ambiguity_relative_tolerance
            ),
        }
        for name, value in values.items():
            if not np.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.density_floor <= 0.0:
            raise ValueError("density_floor must be positive")
        if self.hessian_antisymmetry_tolerance < 0.0:
            raise ValueError("hessian_antisymmetry_tolerance must be non-negative")
        if self.lambda2_ambiguity_absolute_tolerance < 0.0:
            raise ValueError(
                "lambda2_ambiguity_absolute_tolerance must be non-negative"
            )
        if self.lambda2_ambiguity_relative_tolerance < 0.0:
            raise ValueError(
                "lambda2_ambiguity_relative_tolerance must be non-negative"
            )


@dataclass(frozen=True, slots=True)
class NCIFieldBatch:
    """Pointwise NCI numerical fields and explicit validity diagnostics."""

    rho: np.ndarray
    gradient_norm: np.ndarray
    rdg: np.ndarray
    hessian_eigenvalues: np.ndarray
    lambda2: np.ndarray
    signed_density: np.ndarray
    rdg_valid_mask: np.ndarray
    field_valid_mask: np.ndarray
    lambda2_sign_ambiguous_mask: np.ndarray
    hessian_antisymmetry_residual: np.ndarray
    invalid_density_count: int = 0
    invalid_nonfinite_count: int = 0
    invalid_hessian_count: int = 0
    ambiguous_lambda2_count: int = 0


def _validate_arrays(
    rho: np.ndarray,
    gradient: np.ndarray,
    hessian: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    density = np.asarray(rho, dtype=float)
    density_gradient = np.asarray(gradient, dtype=float)
    density_hessian = np.asarray(hessian, dtype=float)
    if density.ndim != 1:
        raise ValueError("rho must be a one-dimensional array")
    if density_gradient.shape != (len(density), 3):
        raise ValueError("gradient must have shape (n_points, 3)")
    if density_hessian.shape != (len(density), 3, 3):
        raise ValueError("hessian must have shape (n_points, 3, 3)")
    return density, density_gradient, density_hessian


def compute_nci_components(
    rho: np.ndarray,
    gradient: np.ndarray,
    hessian: np.ndarray,
    *,
    settings: NCISettings,
) -> NCIFieldBatch:
    """Compute total-density RDG and Hessian-sign NCI fields.

    RDG depends only on ``rho`` and ``gradient``.  Hessian quality therefore
    cannot erase an otherwise valid RDG value.  ``field_valid_mask`` represents
    points where the complete NCI field set (RDG plus Hessian-derived fields) is
    valid.
    """

    density, density_gradient, density_hessian = _validate_arrays(
        rho, gradient, hessian
    )
    n_points = len(density)

    gradient_norm = np.full(n_points, np.nan, dtype=float)
    rdg = np.full(n_points, np.nan, dtype=float)
    eigenvalues = np.full((n_points, 3), np.nan, dtype=float)
    lambda2 = np.full(n_points, np.nan, dtype=float)
    signed_density = np.full(n_points, np.nan, dtype=float)
    antisymmetry_residual = np.full(n_points, np.nan, dtype=float)
    ambiguity_mask = np.zeros(n_points, dtype=bool)

    finite_density = np.isfinite(density)
    finite_gradient = np.all(np.isfinite(density_gradient), axis=1)
    finite_hessian = np.all(np.isfinite(density_hessian), axis=(1, 2))

    gradient_norm[finite_gradient] = np.linalg.norm(
        density_gradient[finite_gradient], axis=1
    )
    rdg_valid = finite_density & finite_gradient & (density > settings.density_floor)
    if np.any(rdg_valid):
        with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
            denominator = _RDG_DENOMINATOR_COEFFICIENT * np.power(
                density[rdg_valid], 4.0 / 3.0
            )
            rdg[rdg_valid] = gradient_norm[rdg_valid] / denominator
        rdg_valid &= np.isfinite(rdg)
        rdg[~rdg_valid] = np.nan

    if np.any(finite_hessian):
        finite_indices = np.flatnonzero(finite_hessian)
        finite_matrices = density_hessian[finite_hessian]
        residuals = np.max(
            np.abs(finite_matrices - np.swapaxes(finite_matrices, 1, 2)),
            axis=(1, 2),
        )
        antisymmetry_residual[finite_indices] = residuals

    hessian_quality_valid = finite_hessian & (
        antisymmetry_residual <= settings.hessian_antisymmetry_tolerance
    )
    if np.any(hessian_quality_valid):
        valid_indices = np.flatnonzero(hessian_quality_valid)
        matrices = density_hessian[hessian_quality_valid]
        symmetric = 0.5 * (matrices + np.swapaxes(matrices, 1, 2))
        values = np.linalg.eigvalsh(symmetric)
        eigenvalues[valid_indices] = values
        lambda2[valid_indices] = values[:, 1]

        finite_signed = finite_density[hessian_quality_valid]
        signed_values = np.full(len(valid_indices), np.nan, dtype=float)
        signed_values[finite_signed] = (
            np.sign(values[finite_signed, 1]) * density[valid_indices[finite_signed]]
        )
        signed_density[valid_indices] = signed_values

        max_abs_eigenvalue = np.max(np.abs(values), axis=1)
        ambiguity_tolerance = np.maximum(
            settings.lambda2_ambiguity_absolute_tolerance,
            settings.lambda2_ambiguity_relative_tolerance * max_abs_eigenvalue,
        )
        ambiguity_mask[valid_indices] = np.abs(values[:, 1]) <= ambiguity_tolerance

    complete_finite = (
        rdg_valid
        & hessian_quality_valid
        & np.all(np.isfinite(eigenvalues), axis=1)
        & np.isfinite(lambda2)
        & np.isfinite(signed_density)
    )

    nonfinite_input = ~(finite_density & finite_gradient & finite_hessian)
    invalid_density = finite_density & (density <= settings.density_floor)
    invalid_hessian = finite_hessian & ~hessian_quality_valid

    return NCIFieldBatch(
        rho=density.copy(),
        gradient_norm=gradient_norm,
        rdg=rdg,
        hessian_eigenvalues=eigenvalues,
        lambda2=lambda2,
        signed_density=signed_density,
        rdg_valid_mask=rdg_valid,
        field_valid_mask=complete_finite,
        lambda2_sign_ambiguous_mask=ambiguity_mask,
        hessian_antisymmetry_residual=antisymmetry_residual,
        invalid_density_count=int(np.count_nonzero(invalid_density)),
        invalid_nonfinite_count=int(np.count_nonzero(nonfinite_input)),
        invalid_hessian_count=int(np.count_nonzero(invalid_hessian)),
        ambiguous_lambda2_count=int(np.count_nonzero(ambiguity_mask)),
    )
