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
