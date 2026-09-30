"""Capability inspection shared by CLI diagnostics and other interfaces."""

from pathlib import Path

from .analysis.registry import _resolve, available_analyses
from .capabilities import evaluate_requirements, infer_capabilities
from .data import OpenWFNData
from .ingest import load_input
from .results import ResultRecord


def capability_payload(data: OpenWFNData, *, input_path: Path | None = None) -> dict[str, object]:
    """Return one deterministic machine-readable capability report."""

    capabilities = infer_capabilities(data)
    analyses: dict[str, object] = {}
    for name in available_analyses():
        definition = _resolve(name)
        availability = evaluate_requirements(data, definition.requirements)
        analyses[name] = {
            "available": availability.available,
            "missing_requirements": list(availability.missing_requirements),
        }

    provenance = data.provenance
    backend = getattr(provenance, "backend", None) if provenance else None
    backend_version = getattr(provenance, "backend_version", None) if provenance else None
    return {
        "input": str(input_path) if input_path is not None else (provenance.source_path if provenance else None),
        "source_format": provenance.source_format if provenance else None,
        "backend": backend or ("native" if provenance is not None else None),
        "backend_version": backend_version,
        "capabilities": {
            name: {"state": capability.state, "reason": capability.reason}
            for name, capability in capabilities.items()
        },
        "analyses": analyses,
    }


def build_capabilities_result(path: Path) -> ResultRecord:
    """Load one input and report data/analysis capabilities without running analyses."""

    data = load_input(path)
    return ResultRecord(kind="capabilities", data=capability_payload(data, input_path=path))
