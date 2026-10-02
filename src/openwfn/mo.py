# src/openwfn/mo.py

from typing import Any, Dict, List

import numpy as np  # type: ignore


def get_homo_lumo_indices(n_alpha_electrons: int, n_beta_electrons: int) -> Dict[str, int]:
    """
    Determine the HOMO and LUMO indices based on the number of electrons.
    Returns 0-based indices for lists/arrays.
    """
    indices = {}
    
    if n_alpha_electrons > 0:
        indices['homo_alpha'] = n_alpha_electrons - 1
        indices['lumo_alpha'] = n_alpha_electrons
        
    if n_beta_electrons > 0 and n_beta_electrons != n_alpha_electrons:
        indices['homo_beta'] = n_beta_electrons - 1
        indices['lumo_beta'] = n_beta_electrons

    return indices


def evaluate_mo(
    r_points: np.ndarray,
    mo_index: int,
    mo_coeffs: List[float],
    basis_data: Dict[str, List[Any]],
    coordinates: List[tuple[float, float, float]]
) -> np.ndarray:
    """
    Legacy placeholder, unavailable; use the normalized scientific evaluator.
    
    Args:
        r_points: (N, 3) matrix of grid points.
        mo_index: 0-based index of the MO to evaluate.
        mo_coeffs: Flat list of MO coefficients.
        basis_data: Parsed basis set data from FCHK.
        coordinates: Atomic coordinates from FCHK.
        
    Returns:
        No values: this unimplemented legacy entry point raises NotImplementedError.
    """
    raise NotImplementedError(
        "Legacy evaluate_mo has no validated implementation. "
        "Use openwfn.analysis.orbitals.evaluate_orbital with normalized CalculationData "
        "or OpenWFNCalculation.orbital_cube instead."
    )
