# src/openwfn/grid.py

import numpy as np  # type: ignore
from typing import Tuple

def make_bounding_box_grid(
    coordinates: list[Tuple[float, float, float]],
    margin: float = 3.0,
    spacing: float = 0.2
) -> Tuple[np.ndarray, Tuple[int, int, int]]:
    """
    Create a 3D rectangular grid around the molecule.
    
    Args:
        coordinates: List of (x, y, z) tuples for each atom in Angstroms.
        margin: Padding around the min/max coordinates in Angstroms.
        spacing: Grid spacing in Angstroms.
        
    Returns:
        points: (N, 3) array of Cartesian coordinates for all grid points.
        shape: (nx, ny, nz) shape of the grid for reshaping.
    """
    if not coordinates:
        return np.empty((0, 3)), (0, 0, 0)

    coords_arr = np.array(coordinates)
    min_bounds = coords_arr.min(axis=0) - margin
    max_bounds = coords_arr.max(axis=0) + margin

    # Generate points in each dimension
    x_points = np.arange(min_bounds[0], max_bounds[0], spacing)
    y_points = np.arange(min_bounds[1], max_bounds[1], spacing)
    z_points = np.arange(min_bounds[2], max_bounds[2], spacing)

    # Make 3D meshgrid
    # indexing='ij' gives (nx, ny, nz) shape matrix matching xyz ordering
    X, Y, Z = np.meshgrid(x_points, y_points, z_points, indexing='ij')

    # Flatten into (N, 3) for vectorized evaluations
    points = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    shape = X.shape

    return points, shape
