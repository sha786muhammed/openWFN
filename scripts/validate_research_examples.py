#!/usr/bin/env python3
"""Generate a larger conjugated example and independently compare its fields.

Validation dependencies only. Constructed geometry is not an optimized
structure; this checks post-processing, not the accuracy of HF/STO-3G.
"""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from importlib.metadata import version
from math import cos, pi, sin
from pathlib import Path

from scripts.validate_everyday_pyscf import validate_case


def validate_biphenyl(directory: Path) -> dict:
    """Build two regular carbon rings joined by a 1.5-angstrom C-C bond."""
    from openwfn.api import load

    atoms = []
    for center, excluded_hydrogen in ((-2.15, 0), (2.15, 3)):
        for index in range(6):
            angle = index * pi / 3
            atoms.append(f'C {center + 1.4*cos(angle):.10f} {1.4*sin(angle):.10f} 0')
        for index in range(6):
            if index != excluded_hydrogen:
                angle = index * pi / 3
                atoms.append(f'H {center + 2.48*cos(angle):.10f} {2.48*sin(angle):.10f} 0')
    case = ('biphenyl', '; '.join(atoms), 'sto-3g', 0, False)
    reference = validate_case(case, directory)
    source = directory / 'biphenyl.molden'
    summary = load(source).analyze('summary')
    return {'atoms': summary.data['atoms'], 'formula': summary.data['formula'],
            'geometry_status': 'constructed, not optimized',
            'geometry_angstrom': atoms, 'method': 'RHF', 'basis': 'STO-3G',
            'charge': 0, 'multiplicity': 1, 'input_sha256': sha256(source.read_bytes()).hexdigest(),
            'dependencies': {name: version(name) for name in ('pyscf', 'cclib', 'qc-iodata', 'numpy', 'scipy')},
            'reference_scope': 'Same wavefunction: PySCF overlap, densities, ESP, populations and MO fields; '
                               'cclib Mayer; independent DOS/PDOS broadening. No chemical-accuracy claim.',
            'reference': reference}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error('Choose an empty output directory to preserve earlier examples.')
    report = validate_biphenyl(args.output_dir)
    (args.output_dir / 'reference.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f"Independent comparisons passed: {report['formula']}, {report['atoms']} atoms")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
