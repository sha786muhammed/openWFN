#!/usr/bin/env python3
"""Compare bounded ESP quadrature with analytic PySCF Coulomb integrals."""
from __future__ import annotations

import argparse
import json
from importlib.metadata import version
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def compare_case(name: str) -> dict:
    from pyscf import lib
    from pyscf.tools import molden

    from openwfn.analysis.density import integrate_density
    from openwfn.analysis.electrostatics import electronic_esp_from_grid, nuclear_esp
    from openwfn.api import load
    from openwfn.services import density_grid

    lib.num_threads(1)
    report = json.loads((ROOT/'validation/everyday-qc/pyscf-report.json').read_text())
    entry = next(case for case in report['cases'] if case['case'] == name)
    source = ROOT/f'examples/everyday-qc/{name}.molden'
    # Use the very same committed wavefunction via an independent parser.
    # Fresh SCF can rotate a singly occupied degenerate OH orbital and therefore
    # produce a genuinely different density despite the same energy/geometry.
    mol, _, coefficients, occupations, _, _ = molden.load(str(source))
    mol.charge, mol.spin = entry['charge'], entry['spin']
    if entry['spin']:
        dm = sum((c*o) @ c.T for c, o in zip(coefficients, occupations, strict=True))
    else:
        dm = (coefficients*occupations) @ coefficients.T
    centroid = mol.atom_coords().mean(axis=0)
    points = centroid + np.array([[2.13, 2.71, 3.29], [8.13, 7.71, 9.29]])
    reference_electronic = []
    for point in points:
        with mol.with_rinv_origin(point):
            reference_electronic.append(-float(np.einsum('ij,ji', dm, mol.intor('int1e_rinv'))))
    reference_electronic = np.array(reference_electronic)
    reference_nuclear = np.sum(mol.atom_charges()/np.linalg.norm(points[:, None]-mol.atom_coords(), axis=2), axis=1)
    data = load(ROOT/f'examples/everyday-qc/{name}.molden').data.calculation
    nuclear = nuclear_esp(data.molecule, points)
    assert np.max(np.abs(nuclear-reference_nuclear)) < 2e-10
    history = []
    spacings = (.3, .2, .1, .07) if name == 'oh_diffuse_uhf' else (.3, .2, .1)
    for spacing in spacings:
        grid = density_grid(data, 'total', spacing, 4.)
        conservation = integrate_density(grid, mol.nelectron)
        electronic = electronic_esp_from_grid(grid, points)
        history.append({'spacing_bohr': spacing, 'padding_bohr': 4., 'grid_points': len(grid.values),
                        'electronic_esp_hartree_per_e': electronic.tolist(),
                        'total_esp_hartree_per_e': (electronic+nuclear).tolist(),
                        'max_absolute_esp_error': float(np.max(np.abs(electronic-reference_electronic))),
                        'electron_count': conservation.electron_count,
                        'electron_count_error': conservation.absolute_error,
                        'conservation_passed': conservation.passed})
    assert history[-1]['max_absolute_esp_error'] < history[0]['max_absolute_esp_error'], (name, history)
    passed = history[-1]['max_absolute_esp_error'] < .005 and history[-1]['conservation_passed']
    return {'case': name, 'input_sha256': entry['input_sha256'], 'points_bohr': points.tolist(),
            'reference_electronic_esp': reference_electronic.tolist(),
            'reference_nuclear_esp': reference_nuclear.tolist(), 'history': history,
            'status': 'passed' if passed else 'partial', 'validation_status': 'Experimental',
            'limitations': 'Two off-nucleus/off-grid points; fine-grid tolerance 0.005 hartree/e. Padding fixed at 4 bohr, not an independent padding convergence study. Near-field singular quadrature, ECPs and arbitrary diffuse tails remain unvalidated.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = {'validation_status': 'Experimental',
              'reference': 'Independent PySCF Molden parser of committed wavefunction; analytic int1e_rinv contraction; independently summed nuclear potential',
              'dependencies': {name: version(name) for name in ('pyscf', 'qc-iodata', 'numpy')},
              'cases': [compare_case(name) for name in ('water', 'oh_diffuse_uhf', 'ammonium_cation')]}
    report['status'] = 'passed' if all(case['status'] == 'passed' for case in report['cases']) else 'partial'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print('ESP comparison status:', report['status'])


if __name__ == '__main__':
    main()
