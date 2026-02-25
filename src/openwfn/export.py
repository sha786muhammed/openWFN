# src/openwfn/export.py

import json
import numpy as np  # type: ignore
from typing import Tuple, List, Dict, Any


def export_vtk(filename: str, grid_points: np.ndarray, grid_shape: Tuple[int, int, int], data: np.ndarray, data_name: str = "density") -> None:
    """
    Export 3D volumetric data to VTK format for ParaView/Mayavi.
    
    Args:
        filename: output .vtk file path.
        grid_points: (N, 3) matrix of coordinates.
        grid_shape: (nx, ny, nz) grid dimensions.
        data: (N,) flat array of values at each grid point.
        data_name: Name of the scalar field.
    """
    nx, ny, nz = grid_shape
    if nx <= 0 or ny <= 0 or nz <= 0:
        raise ValueError("grid_shape must have positive dimensions.")
    if grid_points.shape[0] != nx * ny * nz:
        raise ValueError("grid_points size does not match grid_shape.")
    if len(data) != nx * ny * nz:
        raise ValueError("data size does not match grid_shape.")
    
    with open(filename, 'w') as f:
        f.write("# vtk DataFile Version 3.0\n")
        f.write(f"openWFN {data_name} export\n")
        f.write("ASCII\n")
        f.write("DATASET STRUCTURED_POINTS\n")
        
        # Dimensions
        f.write(f"DIMENSIONS {nx} {ny} {nz}\n")
        
        # Origin (assume grid_points[0] is the min bound since we used meshgrid)
        origin = grid_points[0]
        f.write(f"ORIGIN {origin[0]} {origin[1]} {origin[2]}\n")
        
        # Infer spacing from neighboring points in flattened ijk-order grid.
        spacing_x = (grid_points[ny * nz][0] - grid_points[0][0]) if nx > 1 else 1.0
        spacing_y = (grid_points[nz][1] - grid_points[0][1]) if ny > 1 else 1.0
        spacing_z = (grid_points[1][2] - grid_points[0][2]) if nz > 1 else 1.0
        f.write(f"SPACING {spacing_x} {spacing_y} {spacing_z}\n")
        
        f.write(f"\nPOINT_DATA {len(data)}\n")
        f.write(f"SCALARS {data_name} float 1\n")
        f.write("LOOKUP_TABLE default\n")
        
        # Write data chunked
        for val in data:
            f.write(f"{val:.6e}\n")


def export_csv(filename: str, grid_points: np.ndarray, data: np.ndarray, data_name: str = "value") -> None:
    """Export points and values to a simple CSV."""
    with open(filename, 'w') as f:
        f.write(f"x,y,z,{data_name}\n")
        for (x, y, z), val in zip(grid_points, data):
            f.write(f"{x:.6f},{y:.6f},{z:.6f},{val:.6e}\n")


def export_json(filename: str, properties: Dict[str, Any]) -> None:
    """Dump scalar molecular properties into JSON."""
    with open(filename, 'w') as f:
        json.dump(properties, f, indent=4)
