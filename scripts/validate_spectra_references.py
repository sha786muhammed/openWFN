#!/usr/bin/env python3
"""Compare pinned 20-atom DVB spectra with printed source tables.

Scope: frequencies, source strengths and Gaussian broadening; not experimental
spectra, source-method accuracy or complete NTO transition matrices.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from hashlib import sha256
from pathlib import Path

import numpy as np

from openwfn.api import load

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'examples/research-workflows/spectroscopy/sources.json'
FLOAT = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?'


def _number(value: str) -> float:
    return float(value.replace('D', 'E').replace('d', 'e'))


def _printed_values(text: str, label: str) -> list[float]:
    return [_number(token) for line in re.findall(rf'(?m)^\s*{label}\s*(.+)$', text)
            for token in line.split()]


def _orca_strengths(text: str, marker: str) -> list[float]:
    if marker not in text:
        return []
    values = []
    for line in text.split(marker, 1)[1].splitlines():
        match = re.match(rf'^\s*\d+:\s+{FLOAT}\s+({FLOAT})\b', line)
        if match:
            values.append(_number(match.group(1)))
        elif values:
            break
    return values


def printed_vibrations(text: str, program: str) -> dict:
    if program == 'gaussian':
        return {'frequencies': _printed_values(text, r'Frequencies\s*--'),
                'ir': _printed_values(text, r'IR Inten\s*--'),
                'raman': _printed_values(text, r'Raman Activ\s*--')}
    if program == 'qchem':
        return {'frequencies': _printed_values(text, r'Frequency:'),
                'ir': _printed_values(text, r'IR Intens:'),
                'raman': _printed_values(text, r'Raman Intens:')}
    # These pinned DVB cases are nonlinear: indices 0..5 are rigid motions.
    frequencies = [_number(match.group(2)) for match in
                   re.finditer(rf'(?m)^\s*(\d+):\s+({FLOAT})\s+cm\*\*-1', text)
                   if int(match.group(1)) >= 6]
    return {'frequencies': frequencies, 'ir': _orca_strengths(text, 'IR SPECTRUM'),
            'raman': _orca_strengths(text, 'RAMAN SPECTRUM')}


def printed_excitations(text: str, program: str) -> tuple[list[float], list[float | None]]:
    if program == 'gaussian':
        matches = list(re.finditer(rf'Excited State\s+\d+:.*?({FLOAT})\s+eV.*?f=({FLOAT})', text))
        return ([_number(match.group(1)) for match in matches],
                [_number(match.group(2)) for match in matches])
    if program == 'qchem':
        matches = list(re.finditer(rf'Excited state\s+\d+: excitation energy \(eV\)\s*=\s*({FLOAT})', text))
        energies, strengths = [], []
        for index, match in enumerate(matches):
            stop = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            block = text[match.end():stop]
            strength = re.search(rf'Strength\s*:\s*({FLOAT})', block)
            energies.append(_number(match.group(1)))
            strengths.append(_number(strength.group(1)) if strength else None)
        return energies, strengths
    body = text.split('ABSORPTION SPECTRUM VIA TRANSITION ELECTRIC DIPOLE MOMENTS', 1)[1]
    energies, strengths = [], []
    for line in body.splitlines():
        fields = line.split()
        if fields and fields[0].isdigit():
            energies.append(_number(fields[1]) * 1239.8419843320026 / 1e7)
            strengths.append(None if 'spin forbidden' in line else _number(fields[3]))
        elif energies:
            break
    return energies, strengths


def validate_case(path: Path, name: str) -> dict:
    text = path.read_text()
    calculation = load(path)
    program, task = name.split('-')
    if task == 'td':
        energies, strengths = printed_excitations(text, program)
        states = calculation.analyze('excited-states')
        assert states.data['job_count'] == 1
        rows = states.data['jobs'][0]['states']
        np.testing.assert_allclose([row['energy_ev'] for row in rows], energies, rtol=0, atol=1e-8)
        assert [row['oscillator_strength'] for row in rows] == strengths
        spectrum = calculation.analyze('uvvis-spectrum', fwhm_ev=.2)
        grid = np.array(spectrum.data['energy_ev'])
        eligible = [(energy, strength) for energy, strength in zip(energies, strengths, strict=True)
                    if strength is not None]
        centers, heights = np.array(eligible).T
        width = .2
        count = len(energies)
    else:
        printed = printed_vibrations(text, program)
        modes = calculation.analyze('vibrations')
        assert len(modes.data['modes']) == 54
        np.testing.assert_allclose([row['frequency_cm1'] for row in modes.data['modes']],
                                   printed['frequencies'], rtol=0, atol=1e-8)
        key = 'ir_intensity_km_mol' if task == 'ir' else 'raman_activity_a4_amu'
        np.testing.assert_allclose([row[key] for row in modes.data['modes']],
                                   printed[task], rtol=0, atol=1e-8)
        spectrum = calculation.analyze(f'{task}-spectrum', fwhm_cm1=20.)
        grid = np.array(spectrum.data['frequency_cm1'])
        centers, heights = np.array(printed['frequencies']), np.array(printed[task])
        width, count = 20., 54
    reference = np.sum(heights * np.exp(-4 * np.log(2) *
                       ((grid[:, None] - centers) / width) ** 2), axis=1)
    np.testing.assert_allclose(spectrum.data['intensity'], reference, rtol=0, atol=1e-8)
    return {'name': name, 'checked_count': count, 'status': 'passed',
            'curve_max_error': float(np.max(np.abs(np.array(spectrum.data['intensity']) - reference))),
            'warnings': list(spectrum.warnings), 'validation_status': spectrum.validation_status,
            'provenance': spectrum.provenance, 'units': spectrum.units}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a new report path; earlier evidence is not overwritten.')
    manifest = json.loads(MANIFEST.read_text())
    args.input_dir.mkdir(parents=True, exist_ok=True)
    reports = []
    for entry in manifest['cases']:
        path = args.input_dir / (entry['name'] + '.out')
        url = f"https://raw.githubusercontent.com/cclib/cclib-data/{manifest['upstream_commit']}/{entry['path']}"
        if args.download:
            with urllib.request.urlopen(url, timeout=30) as response:
                content = response.read(5_000_001)
            if len(content) > 5_000_000 or sha256(content).hexdigest() != entry['sha256']:
                raise ValueError('Reference download exceeds bounds or differs from its pinned checksum')
            with path.open('xb') as stream:
                stream.write(content)
        if sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(f"Checksum differs for {entry['name']}")
        reports.append({**validate_case(path, entry['name']), 'source_url': url,
                        'input_sha256': entry['sha256']})
        print(f"Printed-table and curve checks passed: {entry['name']}", flush=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump({'scope': __doc__, 'cases': reports}, stream, indent=2)
        stream.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
