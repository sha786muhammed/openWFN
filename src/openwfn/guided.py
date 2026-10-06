"""Input-independent state and capability choices for guided CLI sessions."""

from dataclasses import dataclass
from pathlib import Path

from .analysis.registry import run_analysis_safe
from .api import OpenWFNCalculation, load
from .data import OpenWFNData
from .inspection import capability_payload
from .palette import Workflow
from .results import ResultRecord


@dataclass(frozen=True)
class GuidedSession:
    source: Path
    calculation: OpenWFNCalculation
    directory: Path
    format_hint: str | None = None

    @property
    def data(self) -> OpenWFNData:
        return self.calculation.data

    @property
    def analyses(self) -> dict:
        return capability_payload(self.data)["analyses"]

    def eligible(self, name: str) -> bool:
        return self.analyses.get(name, {}).get("available", False)


def build_guided_session(path: Path, *, format_hint: str | None = None) -> GuidedSession:
    source = Path(path).expanduser().resolve()
    return GuidedSession(source, load(source, format_hint=format_hint), Path.cwd(), format_hint)


def build_overview(session: GuidedSession) -> ResultRecord:
    """Inspect metadata and existing orbital energies without grids or exports."""
    names = ["summary"]
    if session.eligible("frontier-all"):
        names.append("frontier-all")
    results = {name: run_analysis_safe(session.data, name) for name in names}
    warnings = tuple(dict.fromkeys(warning for result in results.values() for warning in result.warnings))
    return ResultRecord(
        kind="overview",
        data={"results": {name: result.as_dict() for name, result in results.items()},
              "analyses": session.analyses,
              "next_actions": [workflow.command for workflow in available_workflows(session)]},
        status="partial" if any(result.status != "success" for result in results.values()) else "success",
        warnings=warnings,
        provenance=results["summary"].provenance,
    )


def available_workflows(session: GuidedSession) -> tuple[Workflow, ...]:
    data = session.data
    workflows = [Workflow("Overview", "summary")]
    if data.structure is not None and data.periodic is None:
        workflows.extend((Workflow("Geometry and structure", "geometry"),
                          Workflow("Bonds and fragments", "bonds"),
                          Workflow("Export structure", "export")))
    if session.eligible("frontier-all"):
        workflows.append(Workflow("Orbitals and bonding", "orbitals"))
    if session.eligible("mulliken") or session.eligible("hirshfeld"):
        workflows.append(Workflow("Charges and populations", "population"))
    if data.basis is not None and data.total_density is not None:
        workflows.extend((Workflow("Density and electrostatic potential", "density"),
                          Workflow("Check input and numerical consistency", "validate")))
    if session.eligible("vibrations"):
        workflows.append(Workflow("Vibrations and spectra", "vibrations"))
    if session.eligible("excited-states"):
        workflows.append(Workflow("Excited states and UV–Vis", "excited"))
    if data.grids:
        workflows.append(Workflow("Inspect stored grid", "grid"))
    if data.provenance and data.provenance.source_format in {"gaussianlog", "orcalog", "qchemlog", "cp2klog"}:
        workflows.append(Workflow("Source-reported properties", "properties"))
    if data.calculation is not None:
        workflows.append(Workflow("Create a report", "report"))
        if data.basis is not None:
            workflows.append(Workflow("Export offline 3D workbench", "workbench"))
    workflows.extend((Workflow("Why is an analysis unavailable?", "unavailable"),
                      Workflow("Open another file", "file"), Workflow("Quit", "exit")))
    return tuple(workflows)
