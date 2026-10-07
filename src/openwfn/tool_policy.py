"""Read-only input and bounded parameter checks shared by chat and MCP."""

import re
from dataclasses import dataclass
from inspect import signature
from math import isfinite
from pathlib import Path

from .analysis.registry import _resolve, available_analyses

POINT_ANALYSES = frozenset({'elf', 'lol', 'nci', 'density-derivatives',
                            'kinetic-energy-density'})
SPECIAL_ANALYSES = frozenset({'density', 'stored-grid', 'output-properties'})


def explicit_orbital(question: str, previous: str | None = None) -> str | None:
    """Recognize a plain explicit frontier label, not an inferred orbital index."""
    for text in (question, previous or ''):
        labels = set(re.findall(r'\b(homo|lumo)\b(?!\s*[+-]\s*\d)', text.lower()))
        if labels:
            return next(iter(labels)) if len(labels) == 1 else None
    return None


@dataclass(frozen=True)
class ToolPolicy:
    root: Path
    max_file_bytes: int = 100 * 1024 * 1024
    max_basis_functions: int = 256
    max_grid_points: int = 200_000

    def __post_init__(self):
        object.__setattr__(self, 'root', Path(self.root).expanduser().resolve())
        if not self.root.is_dir():
            raise ValueError('The data root must be an existing directory.')
        for value in (self.max_file_bytes, self.max_basis_functions, self.max_grid_points):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError('Resource limits must be positive integers.')

    def checked_path(self, path: str | Path) -> Path:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = self.root / candidate
        candidate = candidate.resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError('Input must be inside the configured data root.')
        if not candidate.is_file():
            raise ValueError('Input must be an existing regular file.')
        if candidate.suffix.casefold() == '.chk':
            raise ValueError('Convert binary .chk to .fchk outside the read-only assistant/MCP.')
        if candidate.stat().st_size > self.max_file_bytes:
            raise ValueError('Input exceeds the configured file-size limit.')
        return candidate


def allowed_parameters(analysis: str) -> tuple[str, ...]:
    if analysis == 'density':
        return ('kind', 'spacing_bohr', 'padding_bohr')
    if analysis in {'stored-grid', 'output-properties'}:
        return ()
    if analysis not in available_analyses():
        raise ValueError(f'Unknown analysis: {analysis}')
    names = signature(_resolve(analysis).runner).parameters
    excluded = {'data', 'settings', 'seeds_bohr', 'chunk_size', 'points_bohr'}
    selected = set(names) - excluded
    if analysis in POINT_ANALYSES:
        selected.update(('x_bohr', 'y_bohr', 'z_bohr'))
    return tuple(sorted(selected))


def validate_parameters(analysis: str, parameters: dict | None) -> dict:
    if parameters is None:
        return {}
    if not isinstance(parameters, dict) or len(parameters) > 32:
        raise ValueError('Parameters must be a mapping with at most 32 entries.')
    allowed = allowed_parameters(analysis)
    clean = {}
    for key, value in parameters.items():
        if key not in allowed:
            raise ValueError(f'Unsupported parameter for {analysis}: {key}')
        enums = {'spin': ('alpha', 'beta', 'all'),
                 'method': ('mulliken', 'lowdin') if analysis == 'orbital-composition' else (),
                 'kind': ('total', 'alpha', 'beta', 'spin') if analysis == 'density' else ()}
        if key in enums and enums[key] and value not in enums[key]:
            raise ValueError(f'{key} must be one of {", ".join(enums[key])}.')
        if value is not None and not isinstance(value, (str, bool, int, float)):
            raise ValueError('Analysis parameters must be JSON scalars.')
        if isinstance(value, str) and len(value) > 80:
            raise ValueError('Analysis parameter strings are limited to 80 characters.')
        if isinstance(value, (int, float)) and (abs(value) > 1e9 or not isfinite(value)):
            raise ValueError('Analysis parameters must be finite and within resource bounds.')
        if key in {'points', 'max_pairs'} and (isinstance(value, bool)
                or not isinstance(value, int) or not 1 <= value <= 4096):
            raise ValueError(f'{key} must be an integer from 1 to 4096.')
        if key in {'spacing_bohr', 'padding_bohr', 'x_bohr', 'y_bohr', 'z_bohr'}:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f'{key} must be a finite number.')
        clean[key] = value
    return clean


def validate_intent_plan(intent, plan, *, resolved_slots=None) -> None:
    """Reject valid-looking plans that change an explicitly requested task."""
    if plan.action != 'analysis':
        permitted = {'ir': (), 'raman': (), 'summary': (),
                     'vibrations': ('state',), 'frontier': ('spin', 'orbital'),
                     'population': ('method',), 'composition': ('projection-method', 'spin', 'orbital'),
                     'density': ('density-operation', 'points')}
        if intent and intent.family in permitted and plan.clarification not in permitted[intent.family]:
            raise ValueError('The clarification does not match the requested property; use guided analysis. No analysis ran.')
        return
    families = {'ir': {'ir-spectrum'}, 'raman': {'raman-spectrum'},
                'vibrations': {'vibrations', 'normal-mode'},
                'frontier': {'frontier', 'beta-frontier', 'frontier-all', 'output-properties'},
                'population': {'mulliken', 'lowdin', 'hirshfeld', 'output-properties'},
                'density': {'density'}, 'summary': {'summary', 'output-properties'},
                'composition': {'orbital-composition'}}
    if intent and plan.analysis not in families.get(intent.family, {plan.analysis}):
        raise ValueError('The model plan does not match the requested property; no analysis ran. Use guided analysis.')
    slots = resolved_slots or {}
    if 'spin' in slots:
        actual = 'beta' if plan.analysis == 'beta-frontier' else plan.parameters.get('spin', 'alpha')
        if plan.analysis == 'frontier-all':
            actual = 'all'
        if actual != slots['spin']:
            raise ValueError('The model plan contradicts the selected orbital channel; no analysis ran.')
    for slot, parameter in (('projection-method', 'method'), ('orbital', 'mo'),
                            ('state', 'mode' if plan.analysis == 'normal-mode' else 'state')):
        if slot in slots and plan.parameters.get(parameter) != slots[slot]:
            raise ValueError(f'The model plan contradicts the selected {slot}; no analysis ran.')
    if 'method' in slots and plan.analysis != slots['method']:
        raise ValueError('The model plan contradicts the selected population method; no analysis ran.')
    if 'points' in slots and any(plan.parameters.get(k) != v for k, v in slots['points'].items()):
        raise ValueError('The model plan contradicts the selected point; no analysis ran.')
