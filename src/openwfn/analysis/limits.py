"""Scientific in-process allocation limits shared by analysis workflows."""

MAX_GRID_POINTS = 2_000_000
MAX_ATOM_QUADRATURE_POINTS = 20_000_000
# Arbitrary point analyses may be as large as an existing volumetric grid.
MAX_POINT_ANALYSIS_POINTS = MAX_GRID_POINTS
# Keep dense NTO decomposition bounded to the existing per-state amplitude ceiling.
MAX_NTO_MATRIX_ELEMENTS = 1_000_000
DEFAULT_AO_WORKING_BYTES = 128 * 1024**2
_FLOAT64_BYTES = 8


def _require_nonnegative_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _require_positive_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def estimate_ao_temporary_bytes(
    point_count: int,
    nao: int,
    requested_components: int,
) -> int:
    """Return the float64 AO field footprint implied by a point request."""

    _require_nonnegative_integer("point_count", point_count)
    _require_positive_integer("nao", nao)
    _require_positive_integer("requested_components", requested_components)
    return point_count * nao * requested_components * _FLOAT64_BYTES


def validate_point_analysis_request(point_count: int) -> None:
    """Reject oversized arbitrary point batches before scientific evaluation."""

    _require_nonnegative_integer("point_count", point_count)
    if point_count > MAX_POINT_ANALYSIS_POINTS:
        raise ValueError(
            f"Point analysis requests {point_count:,} points, exceeding the safety limit of "
            f"{MAX_POINT_ANALYSIS_POINTS:,}; no AO arrays were allocated."
        )


def bounded_point_chunk_size(
    *,
    point_count: int,
    nao: int,
    requested_components: int,
    requested_chunk_size: int | None = None,
    working_bytes: int = DEFAULT_AO_WORKING_BYTES,
) -> int:
    """Return a chunk size bounded by point and AO-field memory ceilings."""

    validate_point_analysis_request(point_count)
    _require_positive_integer("nao", nao)
    _require_positive_integer("requested_components", requested_components)
    _require_positive_integer("working_bytes", working_bytes)
    if requested_chunk_size is not None:
        _require_positive_integer("requested_chunk_size", requested_chunk_size)

    one_point_bytes = estimate_ao_temporary_bytes(1, nao, requested_components)
    if one_point_bytes > working_bytes:
        raise ValueError(
            f"AO temporary request needs {one_point_bytes:,} bytes for one point, exceeding "
            f"the working-memory ceiling of {working_bytes:,} bytes."
        )
    memory_bound = working_bytes // one_point_bytes
    requested = point_count if requested_chunk_size is None else requested_chunk_size
    if point_count == 0:
        return 1
    return min(point_count, requested, memory_bound)
