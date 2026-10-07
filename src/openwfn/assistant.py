"""File-first scientific questions with engine-rendered answers."""

import hashlib
import json
import re
from dataclasses import dataclass, field
from math import prod
from pathlib import Path
from typing import Callable

from .analysis.grids import molecular_grid_layout
from .analysis.registry import run_analysis_safe
from .errors import DataUnavailableError, OpenWFNError
from .guided import build_guided_session, inspect_stored_grid
from .output_properties import read_output
from .presentation import CommandContext, render
from .results import ResultRecord
from .tool_policy import (
    POINT_ANALYSES,
    ToolPolicy,
    allowed_parameters,
    explicit_orbital,
    validate_parameters,
)

_EXPLANATIONS = {
    'none': (frozenset(), ''),
    'orbital-gap': (frozenset({'frontier', 'beta-frontier', 'frontier-all', 'output-properties'}),
        'An orbital energy gap is not an optical excitation energy.'),
    'population': (frozenset({'mulliken', 'lowdin', 'hirshfeld', 'output-properties'}),
        'Atomic charges depend on the partitioning method; compare like with like.'),
    'density-check': (frozenset({'density'}),
        'This is a numerical density integral. Check the conservation error and grid convergence.'),
    'reported': (frozenset({'output-properties'}),
        'These values were reported by the QC program, not recomputed from a wavefunction.'),
}
_CLARIFICATIONS = {
    'question': 'Which property would you like to inspect?',
    'method': 'Which population method: Mulliken, Löwdin, or Hirshfeld?',
    'projection-method': 'Which orbital projection method: Mulliken or Löwdin?',
    'spin': 'Which orbital channel: alpha or beta?',
    'orbital': 'Which orbital: HOMO, LUMO, or a one-based orbital number?',
    'state': 'Which excited state number would you like to inspect?',
    'points': 'Specify a point as x, y, z in bohr for this real-space analysis.',
}
_OUTPUT_FORMATS = {'gaussianlog', 'orcalog', 'qchemlog', 'cp2klog'}


@dataclass(frozen=True)
class AnalysisPlan:
    action: str
    analysis: str | None = None
    parameters: dict = field(default_factory=dict)
    explanation: str = 'none'
    clarification: str = 'question'

    def __post_init__(self):
        if not all(isinstance(value, str) for value in (self.action, self.explanation, self.clarification)):
            raise ValueError('Action, explanation and clarification must be strings.')
        if self.action not in {'analysis', 'clarify'}:
            raise ValueError('The model must request an analysis or clarification.')
        if self.explanation not in _EXPLANATIONS or self.clarification not in _CLARIFICATIONS:
            raise ValueError('Unknown explanation or clarification template.')
        if self.action == 'analysis':
            if not isinstance(self.analysis, str):
                raise ValueError('An analysis name is required.')
            object.__setattr__(self, 'parameters', validate_parameters(self.analysis, self.parameters))
            permitted = _EXPLANATIONS[self.explanation][0]
            if self.explanation != 'none' and self.analysis not in permitted:
                raise ValueError('Explanation does not apply to this analysis.')
        elif self.analysis is not None or self.parameters or self.explanation != 'none':
            raise ValueError('Clarification cannot include a scientific result or analysis.')

    @classmethod
    def from_json(cls, text: str) -> 'AnalysisPlan':
        if not isinstance(text, str) or len(text) > 16_384:
            raise ValueError('The model response exceeds the plan-size limit.')
        def unique_keys(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('Duplicate model response keys are not accepted.')
                result[key] = value
            return result
        payload = json.loads(text, object_pairs_hook=unique_keys)
        if not isinstance(payload, dict) or set(payload) - {
            'action', 'analysis', 'parameters', 'explanation', 'clarification'
        }:
            raise ValueError('The model response must contain only plan fields, not answer prose.')
        if 'action' not in payload:
            raise ValueError('The model response needs an action.')
        return cls(**payload)


@dataclass(frozen=True)
class AssistantAnswer:
    text: str
    record: ResultRecord | None = None


def _direct_plan(question: str) -> AnalysisPlan | None:
    """Route only explicitly supported short requests; other wording uses the model."""
    text = ' '.join(question.casefold().split()).strip(' ?!.')
    text = re.sub(r'^please ', '', text)
    text = re.sub(r'^(?:what (?:is|are) |show (?:me )?|tell me )', '', text)
    text = re.sub(r'^(?:the |my )', '', text)
    # A narrowly supported spelling correction, not fuzzy scientific interpretation.
    text = re.sub(r'\bhumo\b', 'homo', text)
    if text in {'homo', 'homo energy', 'lumo', 'lumo energy', 'homo-lumo gap', 'homo lumo gap'}:
        return AnalysisPlan('analysis', 'frontier-all')
    if text in {'charge', 'spin', 'multiplicity', 'charge and spin', 'charge and multiplicity', 'formula'}:
        return AnalysisPlan('analysis', 'summary')
    return None


def grounded_answer(record: ResultRecord, explanation: str = 'none') -> AssistantAnswer:
    text = render(record, CommandContext(format='plain'))
    if record.status != 'failed' and explanation != 'none':
        # Only engine-known templates reach the answer. No generated prose is displayed.
        if explanation == 'orbital-gap':
            evidence = 'gap_ev' in record.data or bool(record.data.get('frontier_orbitals')) or any(
                isinstance(record.data.get(channel), dict) and 'gap_ev' in record.data[channel]
                for channel in ('alpha', 'beta'))
        elif explanation == 'population':
            evidence = 'atomic_charges' in record.data or bool(record.data.get('reported_atomic_charges'))
        else:
            evidence = True
        if evidence:
            text += '\n' + _EXPLANATIONS[explanation][1] + '\n'
    text += '\nUnits: ' + json.dumps(record.units, ensure_ascii=False) + '\n'
    text += 'Provenance: ' + json.dumps(record.provenance, ensure_ascii=False) + '\n'
    return AssistantAnswer(text, record)


class AssistantSession:
    """Own one selected input; re-inspect it if its content changes.

    ``confirm`` is a user confirmation callback, not a model-controlled field.
    No exports, conversion, shell access or model connection is performed here.
    """

    def __init__(self, path: str | Path, *, data_root: str | Path | None = None,
                 format_hint: str | None = None, max_file_bytes: int = 100 * 1024 * 1024,
                 max_basis_functions: int = 256, max_grid_points: int = 200_000):
        selected = Path(path).expanduser().absolute()
        self.policy = ToolPolicy(Path(data_root) if data_root is not None else selected.parent,
                                 max_file_bytes, max_basis_functions, max_grid_points)
        self.source = self.policy.checked_path(selected)
        self.format_hint = format_hint
        self._sha256 = None
        self._session = None
        self.last_plan = None
        self.last_question = None
        self.refresh()

    def _digest(self):
        source = self.policy.checked_path(self.source)
        digest = hashlib.sha256()
        consumed = 0
        with source.open('rb') as stream:
            while chunk := stream.read(65536):
                consumed += len(chunk)
                if consumed > self.policy.max_file_bytes:
                    raise ValueError('Input exceeds the configured file-size limit.')
                digest.update(chunk)
        return digest.hexdigest()

    def refresh(self):
        sha256 = self._digest()
        if sha256 != self._sha256:
            session = build_guided_session(self.source, format_hint=self.format_hint)
            if self._digest() != sha256:
                raise ValueError('Input changed while being inspected; try again.')
            self._session, self._sha256 = session, sha256
            self.last_plan = None
            self.last_question = None
        return self._session

    def model_context(self) -> dict:
        session = self.refresh()
        catalog = {name: {**availability, 'parameters': list(allowed_parameters(name))}
                   for name, availability in session.analyses.items()}
        density_ready = session.data.basis is not None and session.data.total_density is not None
        catalog['density'] = {'available': density_ready, 'parameters': list(allowed_parameters('density')),
                              'requires_user_confirmation': True,
                              'defaults': {'kind': 'total', 'spacing_bohr': .3, 'padding_bohr': 6.}}
        catalog['stored-grid'] = {'available': bool(session.data.grids), 'parameters': []}
        catalog['output-properties'] = {'available': session.data.provenance.source_format in _OUTPUT_FORMATS,
                                        'parameters': []}
        # No title, raw file, result arrays, source path, or file hash is sent to a model.
        return {'source_format': session.data.provenance.source_format, 'analyses': catalog,
                'previous_question': self.last_question,
                'previous_request': None if self.last_plan is None else {
                    'analysis': self.last_plan.analysis, 'parameters': self.last_plan.parameters},
                'clarifications': list(_CLARIFICATIONS), 'explanations': list(_EXPLANATIONS),
                'point_parameters': 'x_bohr, y_bohr, z_bohr are Cartesian bohr; state/mode/MO indices are one-based'}

    def ask(self, question: str, planner, *, confirm: Callable[[dict], bool] | None = None,
            on_model_request: Callable[[], None] | None = None) -> AssistantAnswer:
        """Route one question, retaining bounded context for a clarification reply."""
        if not isinstance(question, str) or not question.strip() or len(question) > 4000:
            raise ValueError('Ask a non-blank question of at most 4000 characters.')
        context = self.model_context()
        plan = _direct_plan(question)
        if plan is not None and context['source_format'] in _OUTPUT_FORMATS:
            plan = AnalysisPlan('analysis', 'output-properties')
        if plan is None:
            if on_model_request is not None:
                on_model_request()
            plan = planner.plan(question, context)
        if not isinstance(plan, AnalysisPlan):
            raise ValueError('The model must return a validated analysis plan.')
        requested = explicit_orbital(question, self.last_question)
        if plan.analysis == 'orbital-composition' and requested:
            selected = plan.parameters.get('mo', 'homo')
            if not isinstance(selected, str) or selected.strip().lower() != requested:
                raise ValueError(f'The tool request does not match the explicitly requested {requested.upper()}; no analysis ran.')
        if self._digest() != self._sha256:
            self.refresh()
            raise ValueError('Input changed during model planning; ask again for the current file.')
        answer = self.execute(plan, confirm=confirm)
        if plan.action != 'clarify' or self.last_question is None:
            self.last_question = question
        return answer

    def execute(self, plan: AnalysisPlan, *, confirm: Callable[[dict], bool] | None = None) -> AssistantAnswer:
        if plan.action == 'clarify':
            return AssistantAnswer(_CLARIFICATIONS[plan.clarification])
        session = self.refresh()
        analysis = plan.analysis
        parameters = validate_parameters(analysis, plan.parameters)
        try:
            availability = self.model_context()['analyses'][analysis]
            if not availability['available']:
                missing = ', '.join(availability.get('missing_requirements', ()))
                raise DataUnavailableError(f'{analysis} is unavailable for this input. {missing}')
            basis = session.data.basis
            if basis is not None and analysis != 'summary' and basis.n_functions > self.policy.max_basis_functions:
                raise ValueError(f'AO resource limit: {basis.n_functions} basis functions exceed '
                                 f'configured {self.policy.max_basis_functions}.')
            if analysis == 'density':
                kind = parameters.get('kind', 'total')
                spacing = parameters.get('spacing_bohr', .3)
                padding = parameters.get('padding_bohr', 6.)
                _, shape = molecular_grid_layout(session.calculation.molecule, spacing_bohr=spacing,
                    padding_bohr=padding, max_grid_points=self.policy.max_grid_points)
                settings = {'kind': kind, 'spacing_bohr': spacing, 'padding_bohr': padding,
                            'grid_points': prod(shape)}
                if confirm is None or not confirm(settings):
                    return AssistantAnswer('Density needs user confirmation of the displayed grid settings.')
                if self._digest() != self._sha256:
                    raise ValueError('Input changed after grid confirmation; ask again with the current file.')
                record = session.calculation.density(kind, spacing_bohr=spacing, padding_bohr=padding)
            elif analysis == 'stored-grid':
                record = session.calculation._with_provenance(inspect_stored_grid(session.data.grids[0]))
            elif analysis == 'output-properties':
                record = read_output(self.source)
            else:
                if analysis in POINT_ANALYSES:
                    if not {'x_bohr', 'y_bohr', 'z_bohr'} <= parameters.keys():
                        return AssistantAnswer(_CLARIFICATIONS['points'])
                    parameters['points_bohr'] = [[parameters.pop(name) for name in ('x_bohr', 'y_bohr', 'z_bohr')]]
                if analysis == 'qtaim' and len(session.calculation.molecule.atoms) > 32:
                    raise ValueError('QTAIM assistant resource limit: at most 32 centers; use the direct API for larger searches.')
                record = run_analysis_safe(session.data, analysis, **parameters)
            if self._digest() != self._sha256:
                raise ValueError('Input changed during analysis; results were discarded. Ask again.')
            self.last_plan = plan
            explanation = plan.explanation
            if explanation == 'none':
                explanation = {
                    'frontier': 'orbital-gap', 'frontier-all': 'orbital-gap',
                    'beta-frontier': 'orbital-gap', 'mulliken': 'population',
                    'lowdin': 'population', 'hirshfeld': 'population',
                    'density': 'density-check', 'output-properties': 'reported',
                }.get(analysis, 'none')
            return grounded_answer(record, explanation)
        except (OpenWFNError, ValueError, TypeError, OSError) as exc:
            record = session.calculation._with_provenance(ResultRecord.failure(
                kind='assistant_analysis', analysis_name=analysis, analysis_version='1',
                exception=exc, elapsed_seconds=0.))
            return grounded_answer(record)
