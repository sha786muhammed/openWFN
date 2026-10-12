"""Independent real-space and local QTAIM checks; no complete-topology claim."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CASES = ('hydrogen', 'ethylene', 'biphenyl')


def reference_fields(molecule, density_matrix, points):
    """Contract PySCF AO derivatives directly, without openWFN field kernels."""
    from pyscf.dft import numint

    ao = numint.eval_ao(molecule, np.asarray(points), deriv=2)
    values, first = ao[0], ao[1:4]
    rho = np.einsum('pi,ij,pj->p', values, density_matrix, values)
    gradient = 2 * np.einsum('xpi,ij,pj->px', first, density_matrix, values)
    second_indices = ((4, 5, 6), (5, 7, 8), (6, 8, 9))
    hessian = np.empty((len(points), 3, 3))
    for i in range(3):
        for j in range(3):
            hessian[:, i, j] = 2 * (
                np.einsum('pi,ij,pj->p', ao[second_indices[i][j]], density_matrix, values)
                + np.einsum('pi,ij,pj->p', first[i], density_matrix, first[j]))
    tau = .5 * sum(np.einsum('pi,ij,pj->p', axis, density_matrix, axis) for axis in first)
    return rho, gradient, hessian, tau


def validate_case(name: str, directory: Path) -> dict:
    """Generate one closed-shell wavefunction and compare fields and one bond CP."""
    if name not in CASES:
        raise ValueError(f'Unknown reference case: {name}')
    directory = Path(directory)
    source = directory / f'{name}.molden'
    if source.exists():
        raise FileExistsError(source)

    from pyscf import gto, lib, scf
    from pyscf.tools import molden
    from scipy.optimize import root

    from openwfn import load
    from openwfn.analysis.qtaim import QTAIMSettings

    if name == 'hydrogen':
        geometry = 'H 0 0 -.37; H 0 0 .37'
    elif name == 'ethylene':
        geometry = 'C -.67 0 0; C .67 0 0; H -1.23 .93 0; H -1.23 -.93 0; H 1.23 .93 0; H 1.23 -.93 0'
    else:
        recipe = json.loads((ROOT / 'examples/research-workflows/biphenyl/reference.json').read_text())
        geometry = '; '.join(recipe['geometry_angstrom'])
    lib.num_threads(1)
    molecule = gto.M(atom=geometry, basis='sto-3g', spin=0, charge=0, verbose=0)
    mean_field = scf.RHF(molecule)
    mean_field.conv_tol = 1e-11
    mean_field.kernel()
    if not mean_field.converged:
        raise AssertionError(f'Source SCF did not converge: {name}')
    directory.mkdir(parents=True, exist_ok=True)
    molden.from_scf(mean_field, str(source))
    density_matrix = mean_field.make_rdm1()
    calculation = load(source)
    points = np.array([[.21, .37, .29], [-.41, .25, .33], [.55, -.31, .47], [.19, -.49, -.27]])
    rho, gradient, hessian, tau = reference_fields(molecule, density_matrix, points)
    grad2 = np.sum(gradient**2, axis=1)
    uniform_ked = .3 * (3 * np.pi**2)**(2/3) * rho**(5/3)
    reference_elf = 1 / (1 + ((tau - grad2 / (8 * rho)) / uniform_ked)**2)
    reference_lol = uniform_ked / (uniform_ked + tau)
    eigenvalues = np.linalg.eigvalsh(hessian)
    rdg = np.sqrt(grad2) / (2 * (3 * np.pi**2)**(1/3) * rho**(4/3))
    references = {
        'density-derivatives': {'rho': rho, 'gradient': gradient, 'hessian': hessian,
                                'laplacian': np.trace(hessian, axis1=1, axis2=2)},
        'kinetic-energy-density': {'tau': tau},
        'elf': {'values': reference_elf}, 'lol': {'values': reference_lol},
        'nci': {'rho': rho, 'rdg': rdg, 'lambda2': eigenvalues[:, 1],
                'signed_density': np.sign(eigenvalues[:, 1]) * rho},
    }
    records, errors = {}, {}
    for method, expected in references.items():
        parameters = {'points_bohr': points, 'chunk_size': 2}
        if method in {'elf', 'lol'}:
            parameters['channel'] = 'total'
        record = calculation.analyze(method, **parameters)
        if record.status != 'success':
            raise AssertionError((method, record.status, record.warnings))
        errors[method] = {}
        for key, values in expected.items():
            observed = np.asarray(record.data[key])
            np.testing.assert_allclose(observed, values, rtol=2e-6, atol=2e-8, err_msg=f'{name}: {method}/{key}')
            errors[method][key] = float(np.max(np.abs(observed - values)))
        records[method] = record.as_dict()

    def fields(point):
        return reference_fields(molecule, density_matrix, np.asarray([point]))

    seed = np.array([.05, .03, .02])
    reference_root = root(lambda point: fields(point)[1][0], seed,
                          jac=lambda point: fields(point)[2][0], tol=1e-10)
    root_rho, root_gradient, root_hessian, _ = fields(reference_root.x)
    if np.linalg.norm(root_gradient) > 1e-8:
        raise AssertionError(f'Independent stationary point did not converge: {reference_root.message}')
    curvatures = np.linalg.eigvalsh(root_hessian[0])
    if not (np.count_nonzero(curvatures < -1e-8) == 2 and np.count_nonzero(curvatures > 1e-8) == 1):
        raise AssertionError(f'Reference is not a bond critical point: {curvatures}')
    topology = calculation.analyze('qtaim', seeds_bohr=np.asarray([seed]),
        settings=QTAIMSettings(gradient_tolerance=1e-9, max_iterations=96), include_bond_paths=False)
    candidates = [point for point in topology.data['critical_points'] if point['label'] == '(3,-1)']
    if len(candidates) != 1:
        raise AssertionError(f'Expected one local bond CP: {topology.data["critical_points"]}')
    selected = candidates[0]
    np.testing.assert_allclose(selected['position_bohr'], reference_root.x, rtol=0, atol=2e-5)
    np.testing.assert_allclose(selected['hessian_eigenvalues'], curvatures, rtol=2e-6, atol=2e-8)
    np.testing.assert_allclose(selected['rho'], root_rho[0], rtol=2e-6, atol=1e-7)
    records['qtaim'] = topology.as_dict()
    return {
        'case': name, 'atom_count': molecule.natm, 'method': 'RHF', 'basis': 'STO-3G',
        'charge': 0, 'multiplicity': 1, 'geometry_angstrom': geometry,
        'geometry_status': 'constructed, not optimized', 'checks_passed': True,
        'dependencies': {item: version(item) for item in ('pyscf', 'qc-iodata', 'numpy', 'scipy')},
        'input_sha256': sha256(source.read_bytes()).hexdigest(),
        'tolerance': {'field_rtol': 2e-6, 'field_atol': 2e-8, 'cp_position_atol_bohr': 2e-5},
        'scope': 'Same-wavefunction field comparison and one local bond CP; no exhaustive topology, '
                 'basin integration, chemical accuracy or Experimental-status promotion.',
        'points_bohr': points.tolist(),
        'references': {method: {key: values.tolist() for key, values in expected.items()}
                       for method, expected in references.items()},
        'max_absolute_errors': errors,
        'critical_point': {'label': '(3,-1)', 'reference_position_bohr': reference_root.x.tolist(),
            'reference_rho': float(root_rho[0]), 'reference_hessian_eigenvalues': curvatures.tolist(),
            'position_max_error_bohr': float(np.max(np.abs(reference_root.x - selected['position_bohr']))),
            'density_abs_error': abs(float(root_rho[0]) - selected['rho'])},
        'records': records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--case', choices=CASES, action='append')
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error('Choose an empty output directory; earlier results will not be replaced.')
    reports = [validate_case(name, args.output_dir) for name in (args.case or CASES)]
    (args.output_dir / 'reference.json').write_text(json.dumps(reports, indent=2, allow_nan=False) + '\n')
    print('Independent field and local bond-CP checks passed: ' + ', '.join(item['case'] for item in reports))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
