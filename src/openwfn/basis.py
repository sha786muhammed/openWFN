# src/openwfn/basis.py

import numpy as np  # type: ignore

def eval_s_type_gto(r_points: np.ndarray, center: np.ndarray, alpha: np.ndarray, d: np.ndarray) -> np.ndarray:
    """
    Vectorized evaluation of an s-type Contracted Gaussian Type Orbital over N points.
    
    Args:
        r_points: (N, 3) float array of Cartesian coordinates.
        center: (3,) float array of the basis function center.
        alpha: (K,) float array of orbital exponents.
        d: (K,) float array of orbital contraction coefficients.
        
    Returns:
        (N,) float array of the evaluated basis function amplitude at each point.
    """
    # r_squared: shape (N,)
    r_squared = np.sum((r_points - center)**2, axis=1)
    
    # exponentials: shape (N, K)
    # alpha is shape (K,), r_squared is broadcasted by outer product
    exponentials = np.exp(-np.outer(r_squared, alpha))
    
    # Contract with coefficients d: shape (N,)
    return np.dot(exponentials, d)

# P and D type orbital implementations would go here, multiplying the unnormalized
# s-type contracted Gaussians by the corresponding cartesian polynomials (x, y, z, xy, x2-y2, etc.)
