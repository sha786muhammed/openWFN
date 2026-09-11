"""Typed, renderer-independent command results."""

from dataclasses import dataclass, field
from typing import Any, Literal

CapabilityStatus = Literal["Stable", "Validated", "Experimental", "Unsupported"]


@dataclass(frozen=True, slots=True)
class ResultRecord:
    kind: str
    data: dict[str, Any]
    units: dict[str, str] = field(default_factory=dict)
    validation_status: CapabilityStatus = "Stable"
