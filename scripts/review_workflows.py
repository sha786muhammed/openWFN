#!/usr/bin/env python3
"""Run bounded property coverage checks; this is not independent validation.

Keep full results, warnings and settings. A partial result is not a pass.
QTAIM uses two seeds without bond paths; it does not establish full topology.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path

import numpy as np

from openwfn.analysis.qtaim import QTAIMSettings
from openwfn.analysis.registry import available_analyses, run_analysis_safe
from openwfn.api import load
from openwfn.app import CommandContext
from openwfn.inspection import capability_payload
from openwfn.presentation import render

ROOT = Path(__file__).resolve().parents[1]
POINTS = [[.31, .47, .83], [1.23, -.41, .67]]


def iodata_corpus() -> list[tuple[Path, str | None]]:
    """Locate installed upstream inputs without assuming redistribution rights."""
    import iodata

    directory = Path(iodata.__file__).parent / 'test/data'
    if not directory.is_dir():
        raise FileNotFoundError('The installed IOData package does not include its test data.')
    formats = {'.fchk': 'fchk', '.fch': 'fchk', '.molden': 'molden', '.wfn': 'wfn',
               '.wfx': 'wfx', '.mwfn': 'mwfn', '.mkl': 'molekel', '.cube': 'cube',
               '.cub': 'cube', '.xyz': 'xyz', '.sdf': 'sdf', '.pdb': 'pdb'}
    cases = []
    for path in sorted(directory.iterdir()):
        if path.suffix in formats:
            cases.append((path, formats[path.suffix]))
        elif path.suffix in {'.out', '.log'}:
            hint = 'cp2klog' if '.cp2k.' in path.name else None
            cases.append((path, hint))
    return cases


def parameters_for(name: str) -> dict:
    if name in {'density-derivatives', 'kinetic-energy-density', 'elf', 'lol', 'nci'}:
        return {'points_bohr': np.array(POINTS), 'chunk_size': 1}
    if name in {'excited-state', 'nto'}:
        return {'state': 1}
    if name == 'normal-mode':
        return {'mode': 1}
    if name == 'qtaim':
        return {'seeds_bohr': np.array(POINTS), 'include_bond_paths': False,
                'settings': QTAIMSettings(max_iterations=8, max_seeds=2)}
    return {}


def _parameters_record(parameters: dict) -> dict:
    from dataclasses import asdict, is_dataclass
    return {key: value.tolist() if isinstance(value, np.ndarray) else
            asdict(value) if is_dataclass(value) else value
            for key, value in parameters.items()}


def review_file(path: Path, *, format_hint: str | None = None) -> dict:
    source = Path(path)
    report = {'input': str(source), 'input_format_hint': format_hint,
              'independent_validation': False, 'analyses': [], 'parameters': {}}
    try:
        report['input_sha256'] = sha256(source.read_bytes()).hexdigest()
        calculation = load(source, format_hint=format_hint)
    except Exception as exc:
        report.update(load_status='failed', error=f'{type(exc).__name__}: {exc}')
        return report
    report['load_status'] = 'loaded'
    capabilities = capability_payload(calculation.data)['analyses']
    report['capabilities'] = capabilities
    selected_parameters = {name: parameters_for(name) for name in available_analyses()}
    frontier = run_analysis_safe(calculation.data, 'frontier-all')
    if frontier.data.get('reference_kind') != 'restricted_closed_shell':
        for name in ('elf', 'lol'):
            selected_parameters[name]['channel'] = 'alpha'
    operations = [(name, lambda n=name: run_analysis_safe(calculation.data, n, **selected_parameters[n]))
                  for name in available_analyses()]
    operations.extend([
        ('density-integrate', lambda: calculation.density(spacing_bohr=.4, padding_bohr=4)),
        ('esp-point', lambda: calculation.esp((.31, .47, .83))),
        ('geometry', calculation.analyze_geometry),
    ])
    for name, operation in operations:
        parameters = selected_parameters.get(name, {})
        if name == 'density-integrate':
            parameters = {'spacing_bohr': .4, 'padding_bohr': 4}
        elif name == 'esp-point':
            parameters = {'coordinates_angstrom': [.31, .47, .83], 'method': 'integrals'}
        report['parameters'][name] = _parameters_record(parameters)
        missing = capabilities.get(name, {}).get('missing_requirements', [])
        row = {'analysis': name, 'missing_requirements': missing}
        try:
            result = operation()
            row['record'] = result.as_dict()
            row['outcome'] = ('unavailable' if result.error and
                              result.error.category == 'DataUnavailableError' else
                              {'success': 'calculated', 'partial': 'partial', 'failed': 'failed'}[result.status])
            if (name == 'hirshfeld' and result.error and
                    result.error.category == 'ValidationError' and
                    'Unsupported Hirshfeld reference element' in result.error.message):
                row['outcome'] = 'unsupported-scope'
            row['cli_preview'] = render(result, CommandContext(format='plain', compact=True,
                                                               input_path=source))
            json.dumps(row, allow_nan=False)
        except Exception as exc:
            row.update(outcome='failed', error=f'{type(exc).__name__}: {exc}')
        report['analyses'].append(row)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='*', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--input-format')
    parser.add_argument('--iodata-corpus', action='store_true',
                        help='Review installed upstream test inputs, including negative cases')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; choose a new path to preserve earlier evidence.')
    if args.files and args.iodata_corpus:
        parser.error('Choose explicit files or --iodata-corpus, not both.')
    if args.iodata_corpus:
        cases = iodata_corpus()
    elif args.files:
        cases = [(path, args.input_format) for path in args.files]
    else:
        manifest = json.loads((ROOT / 'validation/interop/manifest.json').read_text())
        cases = [(ROOT / entry['path'], entry['format_id']) for entry in manifest['formats']]
        cases.extend((path, None) for path in sorted((ROOT / 'examples/everyday-qc').glob('*.molden')))
    reports = []
    for path, hint in cases:
        print(f'Reviewing {path.name}', flush=True)
        reports.append(review_file(path, format_hint=hint))
    counts = Counter(row['outcome'] for case in reports for row in case['analyses'])
    payload = {'scope': 'Bounded workflow checks, not independent scientific validation',
               'cases': reports, 'outcomes': dict(counts)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(payload, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(counts), sort_keys=True))
    return int(any(case['load_status'] == 'failed' for case in reports) or counts['failed'] > 0)


if __name__ == '__main__':
    raise SystemExit(main())
