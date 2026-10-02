#!/usr/bin/env python3
"""Bounded same-wavefunction molecular comparisons with PySCF and cclib.

Optional validation dependencies only; never part of the runtime scientific core.
Regenerates SCF wavefunctions rather than treating openWFN output as a reference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path

import numpy as np

CASES = (
    ('water', 'O 0 0 0; H 0 -.757 .587; H 0 .757 .587', 'sto-3g', 0, False),
    ('methane', 'C 0 0 0; H .63 .63 .63; H -.63 -.63 .63; H -.63 .63 -.63; H .63 -.63 -.63', 'sto-3g', 0, False),
    ('ammonia', 'N 0 0 .1; H 0 .94 -.23; H .814 -.47 -.23; H -.814 -.47 -.23', '6-31g*', 0, False),
    ('benzene', 'C 1.397 0 0; C .6985 1.20984 0; C -.6985 1.20984 0; C -1.397 0 0; C -.6985 -1.20984 0; C .6985 -1.20984 0; H 2.48 0 0; H 1.24 2.14774 0; H -1.24 2.14774 0; H -2.48 0 0; H -1.24 -2.14774 0; H 1.24 -2.14774 0', 'sto-3g', 0, False),
    ('oh_diffuse_uhf', 'O 0 0 0; H 0 0 .97', '6-31+g*', 1, False),
    ('water_cartesian', 'O 0 0 0; H 0 -.757 .587; H 0 .757 .587', '6-31g*', 0, True),
    ('carbon_dioxide', 'O 0 0 -1.16; C 0 0 0; O 0 0 1.16', '6-31g*', 0, False),
    ('water_dimer', 'O 0 0 0; H 0 -.757 .587; H 0 .757 .587; O 0 0 2.9; H 0 -.757 3.487; H 0 .757 3.487', '6-31+g*', 0, False),
    ('ethanol', 'C 0 0 0; C 1.5 0 0; O 2.1 1.2 0; H -.4 .5 .9; H -.4 .5 -.9; H -.4 -1 0; H 1.9 -.5 .9; H 1.9 -.5 -.9; H 3.05 1.1 0', 'sto-3g', 0, False),
    ('oxygen_triplet', 'O 0 0 -.605; O 0 0 .605', '6-31g*', 2, False),
    ('ammonium_cation', 'N 0 0 0; H .59 .59 .59; H -.59 -.59 .59; H -.59 .59 -.59; H .59 -.59 -.59', '6-31g*', 0, False, 1),
)


def validate_case(case, directory: Path) -> dict:
    from cclib.method import MBO
    from cclib.parser.data import ccData
    from pyscf import gto, lib, scf
    from pyscf.tools import molden
    from scipy.linalg import sqrtm

    from openwfn.analysis.basis import overlap_matrix
    from openwfn.analysis.grids import molecular_grid_points
    from openwfn.analysis.orbitals import evaluate_orbital
    from openwfn.api import load
    from openwfn.orbital_services import select_orbital
    from openwfn.spectral_services import HARTREE_TO_EV

    lib.num_threads(1)
    name, geometry, basis, spin, cartesian = case[:5]
    charge = case[5] if len(case) > 5 else 0
    directory.mkdir(parents=True, exist_ok=True)
    mol = gto.M(atom=geometry, basis=basis, spin=spin, charge=charge, cart=cartesian, verbose=0)
    mf = scf.UHF(mol) if spin else scf.RHF(mol)
    mf.conv_tol = 1e-11
    mf.kernel()
    if not mf.converged:
        raise AssertionError(f'{name}: reference SCF did not converge')
    source = directory / f'{name}.molden'
    molden.from_scf(mf, str(source))
    calc = load(source)
    data = calc.data.calculation
    channels = [('alpha', mf.mo_coeff[0], mf.mo_occ[0], mf.mo_energy[0]),
                ('beta', mf.mo_coeff[1], mf.mo_occ[1], mf.mo_energy[1])] if spin else [
                    ('alpha', mf.mo_coeff, mf.mo_occ, mf.mo_energy)]
    s = mf.get_ovlp()
    # Compare overlap spectra without assuming PySCF and normalized AO ordering.
    overlap_error = float(np.max(np.abs(np.linalg.eigvalsh(s) -
                                       np.linalg.eigvalsh(overlap_matrix(data.basis, data.molecule)))))
    slices = mol.aoslice_by_atom()[:, 2:]
    results = {'case': name, 'basis': basis, 'cartesian': cartesian, 'spin': spin, 'charge': charge,
               'geometry_angstrom': geometry, 'method': 'UHF' if spin else 'RHF',
               'scf_converged': True, 'reference_energy_hartree': float(mf.e_tot),
               'input_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
               'overlap_eigenvalue_max_error': overlap_error, 'orbitals': []}
    # PySCF Cartesian AOs use a shell normalization different from individually
    # normalized openWFN Cartesian AOs. Spectrum equality only applies to pure AOs.
    if not cartesian:
        assert overlap_error < 2e-7, (name, overlap_error)
    for channel, coefficients, occupations, energies in channels:
        for selector in ('homo', 'lumo'):
            orbitals, index = select_orbital(data, selector, channel)
            c = coefficients[:, index]
            points, _, _ = molecular_grid_points(data.molecule, spacing_bohr=.8, padding_bohr=3.)
            reference = mol.eval_gto('GTOval', points) @ c
            actual = evaluate_orbital(data.molecule, data.basis, orbitals, index, points)
            error = float(np.max(np.abs(reference-actual)))
            assert error < 2e-7, (name, channel, selector, 'field', error)
            cube_path = directory / f'{name}_{channel}_{selector}.cube'
            cube = calc.orbital_cube(cube_path, mo=selector, spin=channel,
                                     spacing_bohr=.8, padding_bohr=3., overwrite=True)
            assert cube.status in {'success', 'partial'}, cube.error
            # Check the actual serialized field and z-fastest layout too. Coarse
            # grids intentionally can be partial; no norm-based label promotion.
            lines = cube_path.read_text().splitlines()
            cube_values = np.fromstring(' '.join(lines[6+mol.natm:]), sep=' ')
            cube_error = float(np.max(np.abs(cube_values-reference)))
            assert cube_error < 5e-6, (name, 'cube serialization', cube_error)
            compositions = {}
            for method in ('mulliken', 'lowdin'):
                # Independently use PySCF's population routine on a one-orbital
                # density. Symmetric Loewdin uses SciPy's matrix square root.
                projected = c if method == 'mulliken' else np.asarray(sqrtm(s), dtype=float) @ c
                metric = s if method == 'mulliken' else np.eye(mol.nao_nr())
                populations, _ = scf.hf.mulliken_pop(mol, np.outer(projected, projected), s=metric, verbose=0)
                reference_atoms = np.array([populations[a:b].sum() for a, b in slices]) / (c @ s @ c)
                record = calc.orbital_composition(mo=selector, spin=channel, method=method)
                assert record.status in {'success', 'partial'}, record.error
                observed = np.array([row['fraction'] for row in record.data['atom_contributions']])
                composition_error = float(np.max(np.abs(observed-reference_atoms)))
                # Loewdin fractions depend on AO normalization: PySCF Cartesian
                # and openWFN are different representations, so do not compare.
                if not cartesian or method == 'mulliken':
                    assert composition_error < 2e-7, (name, method, composition_error)
                compositions[method] = {'max_error': composition_error,
                                        'compared': not cartesian or method == 'mulliken',
                                        'reference_atom_fractions': reference_atoms.tolist()}
            results['orbitals'].append({'channel': channel, 'selector': selector,
                                       'mo_number': index+1, 'field_max_error': error,
                                       'serialized_cube_max_error': cube_error,
                                       'cube_status': cube.status, 'cube_warnings': list(cube.warnings),
                                       'composition': compositions})
    names = [f'{atom+1}_AO{ao}' for atom, (a, b) in enumerate(slices) for ao in range(a, b)]
    raw = ccData({'mocoeffs': [c.T for _, c, _, _ in channels],
                  'homos': [int(np.flatnonzero(o > 0)[-1]) for _, _, o, _ in channels],
                  'nbasis': mol.nao_nr(), 'aooverlaps': s, 'aonames': names})
    reference_mbo = MBO(raw, None, 50)
    assert reference_mbo.calculate()
    reference_matrix = reference_mbo.fragresults.sum(axis=0)
    mayer = calc.mayer()
    assert mayer.status == 'success', (name, mayer.error, mayer.warnings)
    mayer_error = float(np.max(np.abs(np.array(mayer.data['bond_order_matrix'])-reference_matrix)))
    assert mayer_error < 2e-7, (name, 'mayer', mayer_error)
    results['mayer_max_error'] = mayer_error
    results['reference_mayer_matrix'] = reference_matrix.tolist()
    # Independent unweighted line-by-line Gaussian expansion on openWFN's grid.
    pdos = calc.pdos(method='mulliken', group_by='atom', sigma_ev=.4)
    assert pdos.status == 'success', (name, pdos.error, pdos.warnings)
    x = np.array(pdos.data['energy_ev'])
    reference_dos = np.zeros_like(x)
    reference_projections = []
    for _, c, _, energies in channels:
        norms = np.einsum('ij,ij->j', c, s @ c)
        ao_weights = c*(s @ c)/norms
        atom_weights = np.array([ao_weights[a:b].sum(axis=0) for a, b in slices])
        kernel = np.exp(-.5*((x[:, None]-energies[None, :]*HARTREE_TO_EV)/.4)**2)/(.4*np.sqrt(2*np.pi))
        reference_dos += kernel.sum(axis=1)
        reference_projections.extend(atom_weights @ kernel.T)
    dos_error = float(np.max(np.abs(reference_dos-pdos.data['total_dos'])))
    pdos_error = float(np.max(np.abs(np.array(reference_projections)-np.array(list(pdos.data['projections'].values())))))
    assert max(dos_error, pdos_error) < 2e-6, (name, 'DOS/PDOS', dos_error, pdos_error)
    results.update(dos_max_error=dos_error, pdos_max_error=pdos_error, status='passed')
    if not cartesian:
        lowdin = calc.pdos(method='lowdin', group_by='atom', sigma_ev=.4)
        assert lowdin.status == 'success', (name, lowdin.error, lowdin.warnings)
        reference_lowdin = []
        root_s = np.asarray(sqrtm(s), dtype=float)
        for _, c, _, energies in channels:
            weights = np.square(root_s @ c)/np.einsum('ij,ij->j', c, s @ c)
            grouped = np.array([weights[a:b].sum(axis=0) for a, b in slices])
            kernel = np.exp(-.5*((x[:, None]-energies[None, :]*HARTREE_TO_EV)/.4)**2)/(.4*np.sqrt(2*np.pi))
            reference_lowdin.extend(grouped @ kernel.T)
        lowdin_error = float(np.max(np.abs(np.array(reference_lowdin)-
                                           np.array(list(lowdin.data['projections'].values())))))
        assert lowdin_error < 2e-6, (name, 'Loewdin PDOS', lowdin_error)
        results['lowdin_pdos_max_error'] = lowdin_error
    return results


def main() -> None:
    from importlib.metadata import version
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    report = {'validation_status': 'Experimental', 'python': platform.python_version(),
              'dependencies': {name: version(name) for name in ('pyscf', 'cclib', 'qc-iodata', 'numpy', 'scipy')},
              'reference_scope': 'Fresh PySCF SCF -> Molden -> IOData -> openWFN; PySCF fields/populations, cclib Mayer, independent Gaussian expansion. Same wavefunction, no method/basis accuracy claim.',
              'cases': [validate_case(case, args.output_dir) for case in CASES]}
    report['status'] = 'passed'
    (args.output_dir/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f"{len(report['cases'])} molecular reference cases passed")


if __name__ == '__main__':
    main()
