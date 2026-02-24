"""
openWFN - open WaveFunction Network
A lightweight toolkit for wavefunction geometry and spatial property analysis.
"""

__version__ = "0.3.0"

from .fchk import read_fchk, parse_fchk_arrays, parse_fchk_scalars, parse_fchk_density, parse_fchk_basis, parse_fchk_mos  # type: ignore
from .geometry import distance, angle, dihedral, detect_bonds  # type: ignore
from .graph import MolecularGraph, build_graph  # type: ignore
from .basis import eval_s_type_gto  # type: ignore
from .density import compute_density  # type: ignore
from .mo import evaluate_mo  # type: ignore
from .grid import make_bounding_box_grid  # type: ignore
from .export import export_vtk, export_json, export_csv  # type: ignore

__all__ = [
    "read_fchk",
    "parse_fchk_arrays",
    "parse_fchk_scalars",
    "parse_fchk_density",
    "parse_fchk_basis",
    "parse_fchk_mos",
    "distance",
    "angle",
    "dihedral",
    "detect_bonds",
    "MolecularGraph",
    "build_graph",
    "eval_s_type_gto",
    "compute_density",
    "evaluate_mo",
    "make_bounding_box_grid",
    "export_vtk",
    "export_json",
    "export_csv",
]