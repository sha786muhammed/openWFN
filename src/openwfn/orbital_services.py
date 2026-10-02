"""Shared orbital-field services; no interface-specific scientific implementations."""
from pathlib import Path

import numpy as np

from .analysis.basis import overlap_matrix
from .analysis.grids import iter_point_chunks, molecular_grid_points, scalar_grid
from .analysis.orbitals import OCCUPATION_THRESHOLD, evaluate_orbital
from .errors import DataUnavailableError
from .exporters.cube import format_cube
from .model import CalculationData, MolecularOrbitals
from .results import ResultRecord


def select_orbital(data: CalculationData, mo: int | str, spin: str) -> tuple[MolecularOrbitals, int]:
    """Resolve a public one-based MO number or an occupation-based frontier label."""
    if spin not in {'alpha', 'beta'}:
        raise ValueError("spin must be 'alpha' or 'beta'")
    orbitals = data.alpha_orbitals if spin == 'alpha' else data.beta_orbitals
    if orbitals is None:
        raise DataUnavailableError(f'{spin.capitalize()} orbital coefficients are not available.')
    if isinstance(mo, str) and mo.lower() in {'homo', 'lumo'}:
        occupied = [i for i, n in enumerate(orbitals.occupations) if n > OCCUPATION_THRESHOLD]
        if not occupied:
            raise DataUnavailableError('HOMO is undefined: no occupied orbital is present.')
        homo = max(occupied, key=lambda i: orbitals.energies[i])
        index = homo
        if mo.lower() == 'lumo':
            virtual = [i for i, n in enumerate(orbitals.occupations)
                       if n <= OCCUPATION_THRESHOLD and orbitals.energies[i] > orbitals.energies[homo]]
            if not virtual:
                raise DataUnavailableError('LUMO is unavailable: no virtual orbital above HOMO.')
            index = min(virtual, key=lambda i: orbitals.energies[i])
    else:
        if isinstance(mo, bool) or not isinstance(mo, (str, int)):
            raise ValueError('MO must be a one-based integer, homo or lumo')
        try:
            index = int(mo) - 1
        except ValueError as exc:
            raise ValueError('MO must be a one-based integer, homo or lumo') from exc
        if not 0 <= index < len(orbitals.energies):
            raise IndexError('MO number is outside the available one-based orbital range')
    return orbitals, index


def orbital_grid(data: CalculationData, mo: int | str, spin: str, spacing_bohr: float,
                 padding_bohr: float, *, chunk_size: int = 65536):
    if data.basis is None:
        raise DataUnavailableError('Orbital cube requires Gaussian basis data.')
    orbitals, index = select_orbital(data, mo, spin)
    if chunk_size <= 0:
        raise ValueError('chunk size must be positive')
    points, origin, shape = molecular_grid_points(data.molecule, spacing_bohr=spacing_bohr,
                                                 padding_bohr=padding_bohr)
    values = np.empty(len(points))
    chunk_size = min(chunk_size, max(1, 8_000_000 // max(1, data.basis.n_functions)))
    offset = 0
    for chunk in iter_point_chunks(points, chunk_size):
        stop = offset + len(chunk)
        values[offset:stop] = evaluate_orbital(data.molecule, data.basis, orbitals, index, chunk)
        offset = stop
    return scalar_grid(data.molecule, values, origin, shape, spacing_bohr, 'bohr^-3/2')


def orbital_cube_export(data: CalculationData, mo: int | str, spin: str, spacing_bohr: float,
                        padding_bohr: float, output_path: Path, overwrite: bool) -> ResultRecord:
    output_path = Path(output_path)
    if output_path.exists() and not overwrite:
        raise FileExistsError(f'Output exists: {output_path}. Pass overwrite=True to replace it.')
    orbitals, index = select_orbital(data, mo, spin)
    grid = orbital_grid(data, mo, spin, spacing_bohr, padding_bohr)
    coefficients = np.asarray(orbitals.coefficients)[:, index]
    norm = float(coefficients @ overlap_matrix(data.basis, data.molecule) @ coefficients)
    integral = float(np.sum(np.square(grid.values)) * spacing_bohr**3)
    warnings = []
    if abs(norm - 1.) > 1e-6:
        warnings.append('MO AO-metric norm differs from one by more than 1e-6; coefficients were not renormalized.')
    if abs(integral - norm) > .005 * max(abs(norm), 1e-12):
        warnings.append('Squared-amplitude grid integral failed 0.5% tolerance against AO-metric norm; refine spacing/padding.')
    source = data.molecule.provenance
    metadata = f'units: bohr^-3/2; mo={index+1}; spin={orbitals.spin}; spacing_bohr={spacing_bohr}; padding_bohr={padding_bohr}; sha256={source.sha256 if source else "unavailable"}'
    lines = format_cube(grid, data.molecule).splitlines()
    lines[1] = metadata
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return ResultRecord(kind='orbital_cube', data={
        'mo_number': index+1, 'spin': orbitals.spin, 'energy_hartree': orbitals.energies[index],
        'occupation': orbitals.occupations[index], 'occupation_source': orbitals.occupation_source,
        'output': str(output_path), 'grid_points': len(grid.values), 'grid_shape': list(grid.shape),
        'spacing': spacing_bohr, 'padding': padding_bohr, 'ao_metric_norm': norm,
        'squared_amplitude_integral': integral, 'grid_norm_error': abs(integral-norm),
        }, units={'amplitude': 'bohr^-3/2', 'spacing': 'bohr', 'padding': 'bohr', 'energy_hartree': 'hartree'},
        validation_status='Experimental', status='partial' if warnings else 'success', warnings=tuple(warnings))
