"""Bounded scalar-grid and cube services for Experimental NCI fields."""

from __future__ import annotations

from math import isfinite
from pathlib import Path
from typing import Literal

import numpy as np

from .analysis.basis import bounded_ao_chunk_size
from .analysis.density import density_matrix_for_kind, evaluate_density
from .analysis.grids import iter_point_chunks, molecular_grid_points, scalar_grid
from .analysis.nci import NCISettings, evaluate_nci
from .errors import DataUnavailableError
from .exporters.cube import write_cube
from .model import CalculationData, VolumetricGrid
from .results import ResultRecord

NCIField = Literal["rho", "lambda2", "signed_density", "rdg"]
_NCI_FIELDS = {"rho", "lambda2", "signed_density", "rdg"}
_NCI_FIELD_UNITS = {
    "rho": "electron/bohr^3",
    "lambda2": "electron/bohr^5",
    "signed_density": "electron/bohr^3",
    "rdg": "dimensionless",
}
_NCI_CONVENTION_VERSION = "nci-rdg-v1"


def _validate_export_inputs(
    field: str,
    *,
    rdg_cap: float | None,
    chunk_size: int,
) -> None:
    if field not in _NCI_FIELDS:
        raise ValueError("NCI field must be rho, lambda2, signed_density, or rdg")
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")
    if field == "rdg":
        if rdg_cap is None or not isfinite(rdg_cap) or rdg_cap <= 0.0:
            raise ValueError("rdg_cap must be a positive finite value for RDG grids")
    elif rdg_cap is not None:
        raise ValueError("rdg_cap is only meaningful for the RDG field")


def _density_source(data: CalculationData) -> str | None:
    return data.total_density.source if data.total_density is not None else None


def _rho_chunk(data: CalculationData, points: np.ndarray) -> np.ndarray:
    if data.basis is None:
        raise DataUnavailableError("NCI grid export requires Gaussian basis-set data.")
    matrix = density_matrix_for_kind(data, "total")
    return np.asarray(
        evaluate_density(data.molecule, data.basis, matrix, points), dtype=float
    )


def _field_chunk(
    data: CalculationData,
    field: NCIField,
    points: np.ndarray,
    *,
    settings: NCISettings,
    rdg_cap: float | None,
) -> tuple[np.ndarray, int, int]:
    """Return one finite scalar chunk and its RDG export diagnostics."""

    if field == "rho":
        values = _rho_chunk(data, points)
        if not np.all(np.isfinite(values)):
            raise ValueError("NCI rho grid contains nonfinite values; cube export aborted")
        return values, 0, 0

    batch = evaluate_nci(data, points, settings=settings)
    if field == "lambda2":
        values = np.asarray(batch.lambda2, dtype=float)
        if not np.all(np.isfinite(values)):
            raise ValueError(
                "NCI lambda2 grid contains invalid or nonfinite Hessian-derived values; "
                "cube export aborted"
            )
        return values, 0, 0

    if field == "signed_density":
        values = np.asarray(batch.signed_density, dtype=float)
        if not np.all(np.isfinite(values)):
            raise ValueError(
                "NCI signed-density grid contains invalid or nonfinite Hessian-derived "
                "values; cube export aborted"
            )
        return values, 0, 0

    assert field == "rdg"
    assert rdg_cap is not None
    values = np.asarray(batch.rdg, dtype=float).copy()
    finite_rho = np.isfinite(batch.rho)
    finite_gradient = np.isfinite(batch.gradient_norm)
    density_tail = finite_rho & finite_gradient & (batch.rho <= settings.density_floor)
    invalid_other = ~batch.rdg_valid_mask & ~density_tail
    if np.any(invalid_other):
        raise ValueError(
            "NCI RDG grid contains invalid values outside the declared low-density tail; "
            "cube export aborted"
        )

    density_tail_count = int(np.count_nonzero(density_tail))
    values[density_tail] = rdg_cap
    finite_valid = batch.rdg_valid_mask & np.isfinite(values)
    clipped = finite_valid & (values > rdg_cap)
    clipped_count = int(np.count_nonzero(clipped))
    values[clipped] = rdg_cap
    if not np.all(np.isfinite(values)):
        raise ValueError("NCI RDG grid contains nonfinite values; cube export aborted")
    return values, clipped_count, density_tail_count


def nci_scalar_grid(
    data: CalculationData,
    field: NCIField,
    spacing_bohr: float,
    padding_bohr: float,
    *,
    settings: NCISettings | None = None,
    rdg_cap: float | None = None,
    chunk_size: int = 65536,
) -> tuple[VolumetricGrid, dict[str, object]]:
    """Evaluate one bounded NCI scalar field on the regular molecular grid.

    RDG export is deliberately presentation-bounded: callers must provide an
    explicit positive ``rdg_cap``. Low-density-tail RDG values are replaced by
    that cap, while any other invalid value aborts the export.
    """

    _validate_export_inputs(field, rdg_cap=rdg_cap, chunk_size=chunk_size)
    if data.basis is None:
        raise DataUnavailableError("NCI grid export requires Gaussian basis-set data.")
    if data.total_density is None:
        raise DataUnavailableError("NCI grid export requires a total AO density matrix.")

    active_settings = settings or NCISettings()
    # molecular_grid_points checks MAX_GRID_POINTS before allocating the grid.
    points, origin, shape = molecular_grid_points(
        data.molecule,
        spacing_bohr=spacing_bohr,
        padding_bohr=padding_bohr,
    )
    bounded_chunk = bounded_ao_chunk_size(data.basis, chunk_size)
    values = np.empty(len(points), dtype=float)
    clipped_finite_count = 0
    density_tail_substitution_count = 0
    offset = 0
    for point_chunk in iter_point_chunks(points, bounded_chunk):
        chunk_values, clipped_count, tail_count = _field_chunk(
            data,
            field,
            point_chunk,
            settings=active_settings,
            rdg_cap=rdg_cap,
        )
        stop = offset + len(chunk_values)
        values[offset:stop] = chunk_values
        offset = stop
        clipped_finite_count += clipped_count
        density_tail_substitution_count += tail_count

    if not np.all(np.isfinite(values)):
        raise ValueError("NCI scalar grid contains nonfinite values; cube export aborted")

    grid = scalar_grid(
        data.molecule,
        values,
        origin,
        shape,
        spacing_bohr,
        _NCI_FIELD_UNITS[field],
    )
    diagnostics: dict[str, object] = {
        "field": field,
        "grid_points": len(values),
        "spacing_bohr": spacing_bohr,
        "padding_bohr": padding_bohr,
        "chunk_size": bounded_chunk,
        "density_floor": active_settings.density_floor,
        "rdg_cap": rdg_cap if field == "rdg" else None,
        "clipped_finite_count": clipped_finite_count,
        "density_tail_substitution_count": density_tail_substitution_count,
        "density_source": _density_source(data),
        "convention_version": _NCI_CONVENTION_VERSION,
        "rdg_formula": "|grad(rho)|/[2(3*pi^2)^(1/3)rho^(4/3)]",
        "hessian_eigenvalue_order": "ascending algebraic",
        "signed_density_formula": "sign(lambda2)*rho",
    }
    return grid, diagnostics


def nci_cube_export(
    data: CalculationData,
    field: NCIField,
    spacing_bohr: float,
    padding_bohr: float,
    output_path: Path,
    overwrite: bool,
    *,
    settings: NCISettings | None = None,
    rdg_cap: float | None = None,
    chunk_size: int = 65536,
) -> ResultRecord:
    """Write a finite, bounded NCI scalar field as an atomic Gaussian cube."""

    output = Path(output_path)
    grid, diagnostics = nci_scalar_grid(
        data,
        field,
        spacing_bohr,
        padding_bohr,
        settings=settings,
        rdg_cap=rdg_cap,
        chunk_size=chunk_size,
    )
    # write_cube publishes atomically only after serialization succeeds.
    write_cube(
        grid,
        data.molecule,
        output,
        overwrite=overwrite,
        comment=(
            f"openWFN Experimental NCI {field}; convention={_NCI_CONVENTION_VERSION}"
        ),
    )
    return ResultRecord(
        kind="nci_cube",
        data={
            **diagnostics,
            "output": str(output),
            "spacing": spacing_bohr,
            "padding": padding_bohr,
            "value_unit": _NCI_FIELD_UNITS[field],
        },
        units={
            "spacing": "bohr",
            "padding": "bohr",
            "value": _NCI_FIELD_UNITS[field],
        },
        validation_status="Experimental",
        status="success",
    )
