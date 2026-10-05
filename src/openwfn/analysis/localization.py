"""Electron-localization descriptors built from density and kinetic-energy fields.

The numerical kernels in this module are deliberately independent of file formats and
presentation. They use openWFN's positive-definite kinetic-energy-density convention,
``tau = 1/2 sum_i n_i |grad psi_i|^2``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from ..model import CalculationData
from ..scientific import orbital_reference_kind
from .realspace import evaluate_density_fields, evaluate_kinetic_energy_density

LocalizationChannel = Literal["total", "alpha", "beta"]
DEFAULT_LOCALIZATION_DENSITY_FLOOR = 1.0e-12
DEFAULT_NEGATIVE_ABSOLUTE_TOLERANCE = 1.0e-12
DEFAULT_NEGATIVE_RELATIVE_TOLERANCE = 1.0e-10
_TOTAL_HEG_COEFFICIENT = (3.0 / 10.0) * (3.0 * np.pi**2) ** (2.0 / 3.0)
_SPIN_HEG_COEFFICIENT = (3.0 / 10.0) * (6.0 * np.pi**2) ** (2.0 / 3.0)


@dataclass(frozen=True, slots=True)
class LocalizationSettings:
    """Numerical thresholds shared by ELF and LOL kernels."""

    density_floor: float = DEFAULT_LOCALIZATION_DENSITY_FLOOR
    negative_absolute_tolerance: float = DEFAULT_NEGATIVE_ABSOLUTE_TOLERANCE
    negative_relative_tolerance: float = DEFAULT_NEGATIVE_RELATIVE_TOLERANCE

    def __post_init__(self) -> None:
        values = {
            "density_floor": self.density_floor,
            "negative_absolute_tolerance": self.negative_absolute_tolerance,
            "negative_relative_tolerance": self.negative_relative_tolerance,
        }
        for name, value in values.items():
            if not np.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.density_floor <= 0.0:
            raise ValueError("density_floor must be positive")
        if self.negative_absolute_tolerance < 0.0:
            raise ValueError("negative_absolute_tolerance must be non-negative")
        if self.negative_relative_tolerance < 0.0:
            raise ValueError("negative_relative_tolerance must be non-negative")


@dataclass(frozen=True, slots=True)
class LocalizationFieldBatch:
    """Numerical localization values plus diagnostics for each supplied point."""

    values: np.ndarray
    valid_mask: np.ndarray
    rho: np.ndarray
    tau: np.ndarray
    reference: np.ndarray
    gradient_norm_squared: np.ndarray | None = None
    von_weizsaecker: np.ndarray | None = None
    pauli_excess: np.ndarray | None = None
    invalid_density_count: int = 0
    invalid_nonfinite_count: int = 0
    invalid_pauli_count: int = 0
    clamped_pauli_count: int = 0
    invalid_ked_count: int = 0
    clamped_ked_count: int = 0


def _validate_rho_tau(rho: np.ndarray, tau: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    density = np.asarray(rho, dtype=float)
    kinetic = np.asarray(tau, dtype=float)
    if density.ndim != 1 or kinetic.ndim != 1:
        raise ValueError("rho and tau must be one-dimensional arrays")
    if len(density) != len(kinetic):
        raise ValueError("rho and tau must have the same length")
    return density, kinetic


def _reference_ked(rho: np.ndarray, *, spin_resolved: bool) -> np.ndarray:
    coefficient = _SPIN_HEG_COEFFICIENT if spin_resolved else _TOTAL_HEG_COEFFICIENT
    reference = np.full(rho.shape, np.nan, dtype=float)
    positive_finite = np.isfinite(rho) & (rho > 0.0)
    with np.errstate(over="ignore", invalid="ignore"):
        reference[positive_finite] = coefficient * np.power(
            rho[positive_finite], 5.0 / 3.0
        )
    return reference


def _negative_tolerance(
    tau: np.ndarray,
    reference: np.ndarray,
    settings: LocalizationSettings,
) -> np.ndarray:
    # Match the documented scale exactly: max(tau, D0, 1). A negative tau cannot
    # enlarge its own tolerance and therefore cannot make a material failure easier
    # to hide.
    scale = np.maximum(np.maximum(tau, reference), 1.0)
    return np.maximum(
        settings.negative_absolute_tolerance,
        settings.negative_relative_tolerance * scale,
    )


def _validate_channel(data: CalculationData, channel: str) -> LocalizationChannel:
    if channel not in {"total", "alpha", "beta"}:
        raise ValueError("localization channel must be total, alpha, or beta")
    if channel == "total" and orbital_reference_kind(data) != "restricted_closed_shell":
        raise ValueError(
            "total ELF/LOL is supported only for demonstrably restricted closed-shell "
            "data; request alpha or beta for open-shell data"
        )
    return channel  # type: ignore[return-value]


def compute_elf_components(
    rho: np.ndarray,
    gradient: np.ndarray,
    tau: np.ndarray,
    *,
    spin_resolved: bool,
    settings: LocalizationSettings,
) -> LocalizationFieldBatch:
    """Compute ELF from density, density gradient, and positive-definite KED arrays.

    Materially negative Pauli excess is preserved as a diagnostic and invalidates the
    corresponding ELF value; it is never squared into an apparently valid result.
    """

    density, kinetic = _validate_rho_tau(rho, tau)
    density_gradient = np.asarray(gradient, dtype=float)
    if density_gradient.ndim != 2 or density_gradient.shape != (len(density), 3):
        raise ValueError("gradient must have shape (n_points, 3)")

    reference = _reference_ked(density, spin_resolved=spin_resolved)
    gradient_norm_squared = np.full(density.shape, np.nan, dtype=float)
    von_weizsaecker = np.full(density.shape, np.nan, dtype=float)
    pauli_excess = np.full(density.shape, np.nan, dtype=float)
    values = np.full(density.shape, np.nan, dtype=float)

    finite_input = (
        np.isfinite(density)
        & np.isfinite(kinetic)
        & np.all(np.isfinite(density_gradient), axis=1)
        & np.isfinite(reference)
    )
    density_valid = finite_input & (density > settings.density_floor)

    gradient_norm_squared[density_valid] = np.einsum(
        "ij,ij->i",
        density_gradient[density_valid],
        density_gradient[density_valid],
    )
    von_weizsaecker[density_valid] = (
        gradient_norm_squared[density_valid] / (8.0 * density[density_valid])
    )
    pauli_excess[density_valid] = (
        kinetic[density_valid] - von_weizsaecker[density_valid]
    )

    tolerance = _negative_tolerance(kinetic, reference, settings)
    tiny_negative = density_valid & (pauli_excess < 0.0) & (
        pauli_excess >= -tolerance
    )
    material_negative = density_valid & (pauli_excess < -tolerance)
    pauli_excess[tiny_negative] = 0.0

    valid = density_valid & ~material_negative
    finite_derived = (
        np.isfinite(gradient_norm_squared)
        & np.isfinite(von_weizsaecker)
        & np.isfinite(pauli_excess)
        & np.isfinite(reference)
    )
    valid &= finite_derived

    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        reference_squared = np.square(reference[valid])
        pauli_squared = np.square(pauli_excess[valid])
        values[valid] = reference_squared / (reference_squared + pauli_squared)
    valid &= np.isfinite(values)
    values[~valid] = np.nan

    invalid_nonfinite = ~finite_input
    invalid_density = finite_input & (density <= settings.density_floor)
    return LocalizationFieldBatch(
        values=values,
        valid_mask=valid,
        rho=density.copy(),
        tau=kinetic.copy(),
        reference=reference,
        gradient_norm_squared=gradient_norm_squared,
        von_weizsaecker=von_weizsaecker,
        pauli_excess=pauli_excess,
        invalid_density_count=int(np.count_nonzero(invalid_density)),
        invalid_nonfinite_count=int(np.count_nonzero(invalid_nonfinite)),
        invalid_pauli_count=int(np.count_nonzero(material_negative)),
        clamped_pauli_count=int(np.count_nonzero(tiny_negative)),
    )


def compute_lol_components(
    rho: np.ndarray,
    tau: np.ndarray,
    *,
    spin_resolved: bool,
    settings: LocalizationSettings,
) -> LocalizationFieldBatch:
    """Compute LOL from density and positive-definite kinetic-energy density arrays."""

    density, kinetic_input = _validate_rho_tau(rho, tau)
    kinetic = kinetic_input.copy()
    reference = _reference_ked(density, spin_resolved=spin_resolved)
    values = np.full(density.shape, np.nan, dtype=float)

    finite_input = np.isfinite(density) & np.isfinite(kinetic) & np.isfinite(reference)
    density_valid = finite_input & (density > settings.density_floor)

    tolerance = _negative_tolerance(kinetic, reference, settings)
    tiny_negative = density_valid & (kinetic < 0.0) & (kinetic >= -tolerance)
    material_negative = density_valid & (kinetic < -tolerance)
    kinetic[tiny_negative] = 0.0

    valid = density_valid & ~material_negative
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        values[valid] = reference[valid] / (reference[valid] + kinetic[valid])
    valid &= np.isfinite(values)
    values[~valid] = np.nan

    invalid_nonfinite = ~finite_input
    invalid_density = finite_input & (density <= settings.density_floor)
    return LocalizationFieldBatch(
        values=values,
        valid_mask=valid,
        rho=density.copy(),
        tau=kinetic,
        reference=reference,
        invalid_density_count=int(np.count_nonzero(invalid_density)),
        invalid_nonfinite_count=int(np.count_nonzero(invalid_nonfinite)),
        invalid_ked_count=int(np.count_nonzero(material_negative)),
        clamped_ked_count=int(np.count_nonzero(tiny_negative)),
    )


def evaluate_elf(
    data: CalculationData,
    points_bohr: np.ndarray,
    *,
    channel: LocalizationChannel = "total",
    chunk_size: int | None = None,
    density_floor: float = DEFAULT_LOCALIZATION_DENSITY_FLOOR,
) -> LocalizationFieldBatch:
    """Evaluate ELF at explicit Bohr points using the shared analytic field engine."""

    selected = _validate_channel(data, channel)
    settings = LocalizationSettings(density_floor=density_floor)
    density = evaluate_density_fields(
        data,
        points_bohr,
        kind=selected,
        chunk_size=chunk_size,
    )
    kinetic = evaluate_kinetic_energy_density(
        data,
        points_bohr,
        kind=selected,
        chunk_size=chunk_size,
    )
    return compute_elf_components(
        density.rho,
        density.gradient,
        kinetic.tau,
        spin_resolved=selected != "total",
        settings=settings,
    )


def evaluate_lol(
    data: CalculationData,
    points_bohr: np.ndarray,
    *,
    channel: LocalizationChannel = "total",
    chunk_size: int | None = None,
    density_floor: float = DEFAULT_LOCALIZATION_DENSITY_FLOOR,
) -> LocalizationFieldBatch:
    """Evaluate LOL at explicit Bohr points using the shared analytic field engine."""

    selected = _validate_channel(data, channel)
    settings = LocalizationSettings(density_floor=density_floor)
    density = evaluate_density_fields(
        data,
        points_bohr,
        kind=selected,
        chunk_size=chunk_size,
    )
    kinetic = evaluate_kinetic_energy_density(
        data,
        points_bohr,
        kind=selected,
        chunk_size=chunk_size,
    )
    return compute_lol_components(
        density.rho,
        kinetic.tau,
        spin_resolved=selected != "total",
        settings=settings,
    )
