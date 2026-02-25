# src/openwfn/density.py

import numpy as np  # type: ignore

def compute_density(
    r_points: np.ndarray,
    density_matrix: np.ndarray,
    # Additional arguments for evaluating basis functions would go here
) -> np.ndarray:
    """
    Compute electron density at given Cartesian points.
    
    rho(r) = sum_{mu, nu} P_{mu, nu} * Phi_mu(r) * Phi_nu(r)
    
    Args:
        r_points: (N, 3) matrix of grid points.
        density_matrix: (K, K) full density matrix P_{mu, nu}.
        
    Returns:
        (N,) array of electron density at each point.
    """
    raise NotImplementedError(
        "Electron density evaluation is not implemented yet. "
        "Basis-function evaluation and matrix contraction are required."
    )
