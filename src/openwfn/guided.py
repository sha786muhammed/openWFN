"""Input-independent state and capability choices for guided CLI sessions."""

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from shlex import join

import numpy as np

from .analysis.registry import run_analysis_safe
from .api import OpenWFNCalculation, load
from .data import OpenWFNData
from .errors import OpenWFNError
from .inspection import capability_payload
from .model import VolumetricGrid
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

    @cached_property
    def analyses(self) -> dict:
        analyses = capability_payload(self.data)["analyses"]
        if analyses.get('hirshfeld', {}).get('available') and self.data.calculation is not None:
            from .analysis.hirshfeld import _validated_references
            from .analysis.hirshfeld_reference import load_hirshfeld_reference_library
            try:
                _validated_references(self.data.calculation, load_hirshfeld_reference_library())
            except (OpenWFNError, ValueError) as exc:
                analyses['hirshfeld'] = {'available': False, 'missing_requirements': [str(exc)]}
        return analyses

    def eligible(self, name: str) -> bool:
        return self.analyses.get(name, {}).get("available", False)


def build_guided_session(path: Path, *, format_hint: str | None = None) -> GuidedSession:
    source = Path(path).expanduser().resolve()
    return GuidedSession(source, load(source, format_hint=format_hint), Path.cwd(), format_hint)


def reproducible_command(session: GuidedSession, *, arguments: tuple[str, ...],
                         output_path: Path | None = None, output_format: str | None = None) -> str:
    tokens = ['openwfn']
    if session.format_hint and (not arguments or arguments[0] != 'properties'):
        tokens.extend(('--input-format', session.format_hint))
    if output_format:
        tokens.extend(('--format', output_format))
    if output_path:
        tokens.extend(('--output', str(output_path)))
    return join([*tokens, str(session.source), *arguments])


def inspect_stored_grid(grid: VolumetricGrid) -> ResultRecord:
    values = np.asarray(grid.values)
    voxel_volume = float(abs(np.linalg.det(np.asarray(grid.axes))))
    return ResultRecord(kind='grid_overview', data={
        'shape': list(grid.shape), 'origin': list(grid.origin), 'axes': grid.axes,
        'points': len(values), 'minimum': float(values.min()), 'maximum': float(values.max()),
        'mathematical_integral': float(values.sum() * voxel_volume),
        'field_identity': 'unverified scalar field', 'recorded_value_unit': grid.value_unit,
    }, units={'origin': 'angstrom', 'axes': 'angstrom', 'minimum': grid.value_unit,
              'maximum': grid.value_unit, 'mathematical_integral': f'{grid.value_unit} * angstrom^3'},
        warnings=('The recorded unit does not prove field identity; no electron-conservation target is inferred.',))


def build_overview(session: GuidedSession) -> ResultRecord:
    """Inspect metadata and existing orbital energies without grids or exports."""
    names = ["summary"]
    if session.eligible("frontier-all"):
        names.append("frontier-all")
    results = {name: run_analysis_safe(session.data, name) for name in names}
    if session.data.structure is None and session.data.grids:
        results['summary'] = session.calculation._with_provenance(inspect_stored_grid(session.data.grids[0]))
    elif session.data.structure is None:
        metadata = session.data.metadata
        results['summary'] = session.calculation._with_provenance(ResultRecord(
            kind='source_metadata', data={'source_program': metadata.source_program,
                'source_program_version': metadata.source_program_version, 'title': metadata.title,
                'energy_hartree': metadata.energy_hartree}, units={'energy_hartree': 'hartree'},
            status='partial', warnings=('Atomic structure is unavailable; only parsed source metadata is shown.',)))
    if session.data.provenance and session.data.provenance.source_format in {'gaussianlog', 'orcalog', 'qchemlog', 'cp2klog'}:
        from .output_properties import read_output
        try:
            results['properties'] = read_output(session.source)
        except (OpenWFNError, ValueError, OSError) as exc:
            results['properties'] = ResultRecord.failure(kind='output_properties', analysis_name='properties',
                analysis_version='1', exception=exc, elapsed_seconds=0., provenance=results['summary'].provenance)
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
    if data.calculation is not None and data.basis is not None:
        workflows.append(Workflow("Create a report", "report"))
        if data.basis is not None:
            workflows.append(Workflow("Export offline 3D workbench", "workbench"))
    workflows.append(Workflow("Ask the scientific assistant", "chat"))
    workflows.extend((Workflow("Why is an analysis unavailable?", "unavailable"),
                      Workflow("Open another file", "file"), Workflow("Quit", "exit")))
    return tuple(workflows)
