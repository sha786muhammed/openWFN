"""Typed, renderer-independent command results."""

from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Literal

CapabilityStatus = Literal["Stable", "Validated", "Experimental", "Unsupported"]
ResultStatus = Literal["success", "partial", "failed"]
RESULT_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True, slots=True)
class ResultError:
    """Machine-readable information about an analysis failure."""

    category: str
    message: str
    recoverable: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "message": self.message,
            "recoverable": self.recoverable,
        }


@dataclass(frozen=True, slots=True)
class ResultRecord:
    kind: str
    data: dict[str, Any]
    units: dict[str, str] = field(default_factory=dict)
    validation_status: CapabilityStatus = "Stable"
    analysis_name: str | None = None
    analysis_version: str = "1"
    status: ResultStatus = "success"
    warnings: tuple[str, ...] = ()
    provenance: dict[str, Any] = field(default_factory=dict)
    elapsed_seconds: float | None = None
    error: ResultError | None = None
    schema_version: str = field(default=RESULT_SCHEMA_VERSION, init=False)

    def __post_init__(self) -> None:
        if not self.kind.strip():
            raise ValueError("kind must not be blank")
        if self.analysis_name is None:
            object.__setattr__(self, "analysis_name", self.kind)
        elif not self.analysis_name.strip():
            raise ValueError("analysis_name must not be blank")
        if not self.analysis_version.strip():
            raise ValueError("analysis_version must not be blank")
        if self.elapsed_seconds is not None and (
            not isfinite(self.elapsed_seconds) or self.elapsed_seconds < 0
        ):
            raise ValueError("elapsed_seconds must be non-negative and finite")
        if self.status == "failed" and self.error is None:
            raise ValueError("failed results require error details")
        if self.status != "failed" and self.error is not None:
            raise ValueError("only failed results may include error details")

    @classmethod
    def failure(
        cls,
        *,
        kind: str,
        analysis_name: str,
        analysis_version: str,
        exception: Exception,
        elapsed_seconds: float,
        warnings: tuple[str, ...] = (),
        provenance: dict[str, Any] | None = None,
        recoverable: bool = True,
    ) -> "ResultRecord":
        """Build a result that preserves failure details without raising."""

        return cls(
            kind=kind,
            data={},
            validation_status="Unsupported",
            analysis_name=analysis_name,
            analysis_version=analysis_version,
            status="failed",
            warnings=warnings,
            provenance=provenance or {},
            elapsed_seconds=elapsed_seconds,
            error=ResultError(type(exception).__name__, str(exception), recoverable),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return the stable, JSON-compatible result envelope."""

        return {
            "analysis_name": self.analysis_name,
            "analysis_version": self.analysis_version,
            "data": self.data,
            "elapsed_seconds": self.elapsed_seconds,
            "error": self.error.as_dict() if self.error else None,
            "kind": self.kind,
            "provenance": self.provenance,
            "schema_version": self.schema_version,
            "status": self.status,
            "units": self.units,
            "validation_status": self.validation_status,
            "warnings": list(self.warnings),
        }
