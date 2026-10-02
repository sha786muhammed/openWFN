"""Shared orbital-energy DOS/PDOS result adapters."""
from math import ceil, erf, isfinite, sqrt

import numpy as np

from .analysis.orbitals import HARTREE_TO_EV
from .analysis.spectra import MAX_SPECTRUM_POINTS, gaussian_spectrum, trapezoid_area
from .errors import DataUnavailableError
from .model import CalculationData
from .results import ResultRecord


def _orbital_channels(data: CalculationData, spin: str):
    if spin not in {'alpha', 'beta', 'all'}:
        raise ValueError("spin must be 'alpha', 'beta' or 'all'")
    channels = []
    for name, orbitals in [('alpha', data.alpha_orbitals), ('beta', data.beta_orbitals)]:
        if spin != 'all' and spin != name:
            continue
        if orbitals is None:
            if spin != 'all':
                raise DataUnavailableError(f'{name.capitalize()} orbital energies unavailable')
            continue
        channels.append((orbitals.spin, orbitals))
    if not channels:
        raise DataUnavailableError('Orbital energies are unavailable')
    return channels


def orbital_dos(data: CalculationData, *, sigma_ev: float = .3, spin: str = 'all',
                energy_min_ev: float | None = None, energy_max_ev: float | None = None,
                points: int | None = None) -> ResultRecord:
    if not isfinite(sigma_ev) or sigma_ev <= 0:
        raise ValueError('Gaussian sigma must be positive and finite')
    channels = _orbital_channels(data, spin)
    energies = np.concatenate([np.asarray(orbitals.energies)*HARTREE_TO_EV for _, orbitals in channels])
    if (energy_min_ev is None) != (energy_max_ev is None):
        raise ValueError('energy range requires both minimum and maximum')
    lower = float(energies.min()-5*sigma_ev) if energy_min_ev is None else energy_min_ev
    upper = float(energies.max()+5*sigma_ev) if energy_max_ev is None else energy_max_ev
    if not isfinite(lower) or not isfinite(upper) or not lower < upper or not isfinite(upper-lower):
        raise ValueError('energy range must be finite and increasing')
    if points is None:
        estimate = (upper-lower)/sigma_ev*5
        if not isfinite(estimate) or estimate > MAX_SPECTRUM_POINTS-1:
            raise ValueError('automatic energy grid exceeds safety limit; broaden sigma or provide a bounded range')
        points = max(2, ceil(estimate)+1)
    if isinstance(points, bool) or not isinstance(points, int) or not 2 <= points <= MAX_SPECTRUM_POINTS:
        raise ValueError('energy points must be an integer from 2 to 100000')
    x = np.linspace(lower, upper, points)
    spectra = {name: gaussian_spectrum(np.asarray(orbitals.energies)*HARTREE_TO_EV, x, sigma_ev)
               for name, orbitals in channels}
    total = sum(spectra.values())
    expected_area = sum(.5*(erf((upper-energy)/(sqrt(2)*sigma_ev))-erf((lower-energy)/(sqrt(2)*sigma_ev)))
                        for energy in energies)
    integral = trapezoid_area(total, x)
    warnings = []
    if expected_area < .995*len(energies):
        warnings.append('Selected energy range omits more than 0.5% of Gaussian orbital weight.')
    if (upper-lower)/(points-1) > sigma_ev/3:
        warnings.append('Energy grid is too coarse for sigma; increase points for resolved broadening.')
    if abs(integral-expected_area) > .005*max(expected_area, 1e-12):
        warnings.append('DOS numerical integral fails 0.5% tolerance against analytic truncated Gaussian area.')
    return ResultRecord(kind='orbital_dos', data={
        'energy_ev': x.tolist(), 'total_dos': total.tolist(),
        'channels': {name: value.tolist() for name, value in spectra.items()},
        'sigma_ev': sigma_ev, 'energy_min_ev': lower, 'energy_max_ev': upper,
        'orbital_count': len(energies), 'integrated_dos': integral,
        'analytic_truncated_area': expected_area, 'counting': 'one per supplied spatial orbital per channel; no occupation weighting',
    }, units={'energy_ev': 'eV', 'total_dos': 'orbitals/eV', 'channels': 'orbitals/eV', 'sigma_ev': 'eV'},
        validation_status='Experimental', status='partial' if warnings else 'success', warnings=tuple(warnings))


def orbital_pdos(data: CalculationData, *, group_by: str = 'atom', method: str = 'lowdin',
                 sigma_ev: float = .3, spin: str = 'all', energy_min_ev: float | None = None,
                 energy_max_ev: float | None = None, points: int | None = None) -> ResultRecord:
    from .analysis.basis import overlap_matrix
    from .analysis.composition import orbital_weights
    from .analysis.spectra import MAX_SPECTRUM_VALUES
    from .constants import Z_TO_SYMBOL

    if group_by not in {'atom', 'element', 'angular'}:
        raise ValueError("PDOS group_by must be 'atom', 'element' or 'angular'")
    if data.basis is None:
        raise DataUnavailableError('PDOS requires Gaussian basis and orbital coefficients.')
    dos = orbital_dos(data, sigma_ev=sigma_ev, spin=spin, energy_min_ev=energy_min_ev,
                      energy_max_ev=energy_max_ev, points=points)
    channels = _orbital_channels(data, spin)
    x = np.asarray(dos.data['energy_ev'])
    labels = []
    for shell in data.basis.shells:
        symbol = Z_TO_SYMBOL.get(data.molecule.atoms[shell.atom_index].atomic_number,
                                 f'Z{data.molecule.atoms[shell.atom_index].atomic_number}')
        for offset in range(shell.n_functions):
            momentum = (0 if offset == 0 else 1) if shell.angular_momentum == -1 else shell.angular_momentum
            label = f'{symbol}{shell.atom_index+1}' if group_by == 'atom' else symbol if group_by == 'element' else f'l={momentum}'
            labels.append(label)
    groups = list(dict.fromkeys(labels))
    if len(groups)*len(x)*len(channels) > MAX_SPECTRUM_VALUES:
        raise ValueError('PDOS exceeds two-million-value projection safety limit; reduce points or group by element/angular')
    overlap = overlap_matrix(data.basis, data.molecule)
    projections = {}
    warnings = list(dos.warnings)
    max_norm_error = 0.
    diagnostic_records = {}
    for name, orbitals in channels:
        weights, norms, diagnostics = orbital_weights(np.asarray(orbitals.coefficients), overlap, method)
        max_norm_error = max(max_norm_error, float(np.max(np.abs(norms-1.))))
        diagnostic_records[name] = diagnostics
        # Group rows in normalized AO order; SP angular labels split s/p above.
        grouped = np.zeros((len(groups), weights.shape[1]))
        group_indices = {label: i for i, label in enumerate(groups)}
        for label, row in zip(labels, weights, strict=True):
            grouped[group_indices[label]] += row
        broadened = gaussian_spectrum(np.asarray(orbitals.energies)*HARTREE_TO_EV, x, sigma_ev, grouped)
        projections.update({f'{name}:{label}': broadened[i].tolist() for i, label in enumerate(groups)})
        condition = diagnostics['overlap_condition_number']
        if diagnostics['overlap_rank_deficient'] or diagnostics['overlap_min_eigenvalue'] < 1e-8 or (condition is not None and condition > 1e10):
            warnings.append('PDOS overlap is ill-conditioned; projections may be unreliable.')
    if max_norm_error > 1e-6:
        warnings.append('PDOS raw MO metric norms fail 1e-6 tolerance; normalized projections do not repair source orbitals.')
    projected_sum = np.sum(np.asarray(list(projections.values())), axis=0)
    residual = float(np.max(np.abs(projected_sum-np.asarray(dos.data['total_dos']))))
    if residual > 1e-10:
        warnings.append('Projected DOS sum differs from total DOS by more than 1e-10 orbitals/eV.')
    return ResultRecord(kind='orbital_pdos', data={**dos.data, 'projections': projections,
        'projection_method': method, 'group_by': group_by, 'max_raw_mo_norm_error': max_norm_error,
        'projection_sum_max_error': residual, 'overlap_diagnostics': diagnostic_records},
        units={**dos.units, 'projections': 'orbitals/eV', 'projection_sum_max_error': 'orbitals/eV'},
        validation_status='Experimental', status='partial' if warnings else 'success',
        warnings=tuple(dict.fromkeys(warnings)))
