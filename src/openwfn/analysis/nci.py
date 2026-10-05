"""Noncovalent-interaction fields from density derivatives.

The numerical kernel in this module is independent of file formats, cube export,
and presentation. It follows the total-density NCI reduced-density-gradient
convention and keeps RDG validity separate from Hessian-dependent lambda2
validity.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..model import CalculationData
from ..results import ResultRecord
from .realspace import evaluate_density_fields

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

    RDG depends only on ``rho`` and ``gradient``. Hessian quality therefore
    cannot erase an otherwise valid RDG value. ``field_valid_mask`` represents
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


def evaluate_nci(
    data: CalculationData,
    points_bohr: np.ndarray,
    *,
    chunk_size: int | None = None,
    settings: NCISettings | None = None,
) -> NCIFieldBatch:
    """Evaluate total-density NCI/RDG fields at explicit Cartesian Bohr points."""

    active_settings = settings or NCISettings()
    fields = evaluate_density_fields(
        data,
        points_bohr,
        kind="total",
        chunk_size=chunk_size,
    )
    return compute_nci_components(
        fields.rho,
        fields.gradient,
        fields.hessian,
        settings=active_settings,
    )


def _nullable_1d(values: np.ndarray) -> list[float | None]:
    array = np.asarray(values, dtype=float)
    return [float(value) if np.isfinite(value) else None for value in array]


def _nullable_2d(values: np.ndarray) -> list[list[float | None]]:
    array = np.asarray(values, dtype=float)
    return [
        [float(value) if np.isfinite(value) else None for value in row]
        for row in array
    ]


def _is_post_hf_method(method: str | None) -> bool:
    if not method:
        return False
    normalized = method.upper().replace("-", "").replace("_", "").replace(" ", "")
    candidates = [normalized]
    for prefix in ("RO", "R", "U"):
        if normalized.startswith(prefix):
            candidates.append(normalized[len(prefix) :])
    families = ("MP2", "MP3", "MP4", "CC", "CI", "QCI")
    return any(candidate.startswith(families) for candidate in candidates)


def _nci_warnings(data: CalculationData, batch: NCIFieldBatch) -> tuple[str, ...]:
    warnings: list[str] = []
    if batch.invalid_density_count:
        warnings.append(
            f"{batch.invalid_density_count} NCI point(s) were at or below the declared "
            "density floor; RDG is reported as null at those points."
        )
    if batch.invalid_nonfinite_count:
        warnings.append(
            f"{batch.invalid_nonfinite_count} NCI point(s) had nonfinite density or "
            "derivative input fields; affected outputs are reported as null."
        )
    if batch.invalid_hessian_count:
        warnings.append(
            f"{batch.invalid_hessian_count} NCI point(s) exceeded the declared Hessian "
            "antisymmetry tolerance; Hessian-derived outputs are reported as null."
        )
    if batch.ambiguous_lambda2_count:
        warnings.append(
            f"{batch.ambiguous_lambda2_count} NCI point(s) have numerically ambiguous "
            "lambda2 sign; raw eigenvalues are retained and the sign should not be "
            "interpreted as reliably attractive or repulsive."
        )
    matrix = data.total_density
    if (
        matrix is not None
        and str(matrix.source).lower() == "scf"
        and _is_post_hf_method(data.molecule.metadata.method)
    ):
        method = data.molecule.metadata.method or "post-HF"
        warnings.append(
            f"{method} calculation is using the SCF density for NCI because no supported "
            "post-SCF density was selected."
        )
    return tuple(warnings)


def nci(
    data: CalculationData,
    *,
    points_bohr: np.ndarray,
    chunk_size: int | None = None,
    settings: NCISettings | None = None,
) -> ResultRecord:
    """Return an Experimental total-density NCI/RDG result envelope."""

    active_settings = settings or NCISettings()
    batch = evaluate_nci(
        data,
        points_bohr,
        chunk_size=chunk_size,
        settings=active_settings,
    )
    points = np.asarray(points_bohr, dtype=float)
    density_source = data.total_density.source if data.total_density is not None else None
    warnings = _nci_warnings(data, batch)
    return ResultRecord(
        kind="nci_rdg",
        data={
            "points_bohr": points.tolist(),
            "rho": _nullable_1d(batch.rho),
            "gradient_norm": _nullable_1d(batch.gradient_norm),
            "rdg": _nullable_1d(batch.rdg),
            "hessian_eigenvalues": _nullable_2d(batch.hessian_eigenvalues),
            "lambda2": _nullable_1d(batch.lambda2),
            "signed_density": _nullable_1d(batch.signed_density),
            "rdg_valid_mask": batch.rdg_valid_mask.astype(bool).tolist(),
            "field_valid_mask": batch.field_valid_mask.astype(bool).tolist(),
            "lambda2_sign_ambiguous_mask": (
                batch.lambda2_sign_ambiguous_mask.astype(bool).tolist()
            ),
            "hessian_antisymmetry_residual": _nullable_1d(
                batch.hessian_antisymmetry_residual
            ),
            "density_source": density_source,
            "chunk_size": chunk_size,
            "thresholds": {
                "density_floor": active_settings.density_floor,
                "hessian_antisymmetry_tolerance": (
                    active_settings.hessian_antisymmetry_tolerance
                ),
                "lambda2_ambiguity_absolute_tolerance": (
                    active_settings.lambda2_ambiguity_absolute_tolerance
                ),
                "lambda2_ambiguity_relative_tolerance": (
                    active_settings.lambda2_ambiguity_relative_tolerance
                ),
            },
            "diagnostics": {
                "invalid_density_count": batch.invalid_density_count,
                "invalid_nonfinite_count": batch.invalid_nonfinite_count,
                "invalid_hessian_count": batch.invalid_hessian_count,
                "ambiguous_lambda2_count": batch.ambiguous_lambda2_count,
            },
            "conventions": {
                "coordinates": "Cartesian bohr",
                "density_channel": "total",
                "rdg_formula": "|grad(rho)|/[2(3*pi^2)^(1/3)rho^(4/3)]",
                "hessian_eigenvalue_order": "ascending algebraic",
                "hessian_symmetrization": "0.5*(H+H.T) after antisymmetry check",
                "signed_density_formula": "sign(lambda2)*rho",
                "invalid_values": "null",
            },
        },
        units={
            "points_bohr": "bohr",
            "rho": "electron/bohr^3",
            "gradient_norm": "electron/bohr^4",
            "rdg": "dimensionless",
            "hessian_eigenvalues": "electron/bohr^5",
            "lambda2": "electron/bohr^5",
            "signed_density": "electron/bohr^3",
            "hessian_antisymmetry_residual": "electron/bohr^5",
        },
        validation_status="Experimental",
        status="success" if bool(np.all(batch.field_valid_mask)) else "partial",
        warnings=warnings,
    )
