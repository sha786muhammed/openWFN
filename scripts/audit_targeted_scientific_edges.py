#!/usr/bin/env python3
"""Throwaway focused scientific edge-case audit for openWFN 0.8.1."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from openwfn import load
from openwfn.services import electrostatic_potential_point


@dataclass
class Finding:
    name: str
    status: str
    detail: str


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    root = args.input_root / 'iodata/iodata/test/data'
    paths = {
        'lih': root / 'li_h_3-21G_hf_g09.fchk',
        'ch3': root / 'ch3_hf_sto3g.fchk',
        'h': root / 'h_sto3g.fchk',
        'mp2': root / 'nitrogen-mp2.fchk',
        'mp3': root / 'nitrogen-mp3.fchk',
        'ci': root / 'nitrogen-ci.fchk',
        'ghost': root / 'water_dimer_ghost.fchk',
    }
    findings: list[Finding] = []

    def record(name: str, ok: bool, detail: str) -> None:
        findings.append(Finding(name, 'passed' if ok else 'failed', detail))

    def capture(name: str, fn):
        try:
            value = fn()
        except Exception as exc:
            findings.append(Finding(name, 'failed', f'{type(exc).__name__}: {exc}'))
            return None
        findings.append(Finding(name, 'passed', repr(value)))
        return value

    # Real UHF LiH doublet: both spin channels and spin densities should work.
    lih = load(paths['lih'])
    all_result = capture('lih-uhf-all', lambda: lih.orbitals('all'))
    if all_result is not None:
        record('lih-reference-kind', all_result.data.get('reference_kind') == 'unrestricted', str(all_result.data))
        record('lih-beta-present', all_result.data.get('beta') is not None, str(all_result.data.get('beta')))
    capture('lih-beta-frontier', lambda: lih.orbitals('beta'))
    for kind in ('total', 'alpha', 'beta', 'spin'):
        capture('lih-density-' + kind, lambda kind=kind: lih.density(kind, spacing_bohr=0.25, padding_bohr=6.0))

    # Real UHF CH3 radical.
    ch3 = load(paths['ch3'])
    ch3_all = capture('ch3-uhf-all', lambda: ch3.orbitals('all'))
    if ch3_all is not None:
        record('ch3-reference-kind', ch3_all.data.get('reference_kind') == 'unrestricted', str(ch3_all.data))
        record('ch3-beta-present', ch3_all.data.get('beta') is not None, str(ch3_all.data.get('beta')))
    for kind in ('alpha', 'beta', 'spin'):
        capture('ch3-density-' + kind, lambda kind=kind: ch3.density(kind, spacing_bohr=0.30, padding_bohr=5.0))

    # One-electron UHF edge: beta orbitals exist but beta occupation is zero.
    hydrogen = load(paths['h'])
    record('hydrogen-beta-channel-parsed', hydrogen.data.beta_orbitals is not None, str(hydrogen.data.beta_orbitals is not None))
    h_all = capture('hydrogen-uhf-all', lambda: hydrogen.orbitals('all'))
    if h_all is not None:
        record('hydrogen-reference-kind', h_all.data.get('reference_kind') == 'unrestricted', str(h_all.data))
        record('hydrogen-overall-homo-alpha', h_all.data.get('overall_homo_spin') == 'alpha', str(h_all.data))
    capture('hydrogen-spin-density', lambda: hydrogen.density('spin', spacing_bohr=0.20, padding_bohr=6.0))

    # Real post-HF files contain correlated density records. 0.8.1 documents
    # explicit SCF use with a warning rather than silently claiming correlated density.
    for label in ('mp2', 'mp3', 'ci'):
        calc = load(paths[label])
        checks = (
            ('population', lambda calc=calc: calc.population('mulliken')),
            ('density', lambda calc=calc: calc.density('total', spacing_bohr=0.30, padding_bohr=5.0)),
            ('esp', lambda calc=calc: electrostatic_potential_point(calc.data, (0.0, 0.0, 5.0), 'electronic', 0.30, 5.0)),
        )
        for name, fn in checks:
            result = capture('posthf-' + label + '-' + name, fn)
            if result is None:
                continue
            source = result.data.get('density_source')
            warning_text = ' '.join(result.warnings).lower()
            record('posthf-' + label + '-' + name + '-source', source == 'scf', 'density_source=' + str(source))
            record('posthf-' + label + '-' + name + '-warning', 'scf' in warning_text and ('post-hf' in warning_text or 'correlated' in warning_text), 'warnings=' + repr(result.warnings))

    # Real six-center ghost FCHK from IOData: three physical atoms + three ghosts.
    ghost = load(paths['ghost'])
    summary = capture('ghost-real-summary', lambda: ghost.analyze('summary'))
    if summary is not None:
        physical = summary.data.get('physical_nuclei')
        ghost_count = summary.data.get('ghost_centers')
        centers = summary.data.get('centers')
        formula = summary.data.get('formula')
        record('ghost-real-counts', physical == 3 and ghost_count == 3 and centers == 6, f'physical={physical}; ghosts={ghost_count}; centers={centers}')
        record('ghost-real-formula', formula == 'H2O', 'formula=' + str(formula))
    ghost_esp = capture('ghost-real-nuclear-esp', lambda: electrostatic_potential_point(ghost.data, (0.0, 0.0, 10.0), 'nuclear', 0.30, 5.0))
    if ghost_esp is not None:
        record('ghost-real-nuclear-esp-value', isinstance(ghost_esp.data.get('value'), (int, float)), str(ghost_esp.data))

    # CLI parity for the most important edge cases.
    commands = (
        ('cli-lih-all', paths['lih'], ['orbitals', 'frontier', '--spin', 'all']),
        ('cli-hydrogen-all', paths['h'], ['orbitals', 'frontier', '--spin', 'all']),
        ('cli-posthf-mp2-pop', paths['mp2'], ['population', 'mulliken']),
        ('cli-ghost-summary', paths['ghost'], ['summary']),
    )
    for name, path, extra in commands:
        proc = subprocess.run(['openwfn', '--format', 'json', str(path), *extra], text=True, capture_output=True, check=False)
        record(name, proc.returncode == 0, f'returncode={proc.returncode}; stdout={proc.stdout[-400:]}; stderr={proc.stderr[-400:]}')

    failures = [item for item in findings if item.status == 'failed']
    payload = {
        'summary': {'total': len(findings), 'passed': len(findings) - len(failures), 'failed': len(failures)},
        'findings': [asdict(item) for item in findings],
    }
    (args.output_dir / 'targeted-audit.json').write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    lines = ['# Targeted scientific edge audit', '', f'Total: {len(findings)}  Passed: {len(findings) - len(failures)}  Failed: {len(failures)}', '', '| Check | Status | Detail |', '|---|---|---|']
    for item in findings:
        detail = item.detail.replace('|', '\\|').replace('\n', ' ')
        lines.append(f'| {item.name} | {item.status} | {detail} |')
    (args.output_dir / 'targeted-audit.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
