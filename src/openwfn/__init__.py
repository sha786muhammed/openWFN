"""
openWFN - open WaveFunction Network
A lightweight toolkit for wavefunction geometry and spatial property analysis.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("openwfn")
except PackageNotFoundError:
    __version__ = "0+unknown"

from .analysis.registry import available_analyses, run_analysis
from .api import OpenWFNCalculation, load
from .basis import eval_s_type_gto  # type: ignore
from .density import compute_density  # type: ignore
from .export import export_csv, export_json, export_molecule_viewer, export_vtk  # type: ignore
from .fchk import (  # type: ignore
    parse_fchk_arrays,
    parse_fchk_basis,
    parse_fchk_density,
    parse_fchk_mos,
    parse_fchk_scalars,
    read_fchk,
)
from .geometry import angle, detect_bonds, dihedral, distance  # type: ignore
from .graph import MolecularGraph, build_graph  # type: ignore
from .grid import make_bounding_box_grid  # type: ignore
from .mo import evaluate_mo  # type: ignore
from .model import (
    MODEL_SCHEMA_VERSION,
    BoundaryConditions,
    CalculationData,
    Provenance,
)
from .results import RESULT_SCHEMA_VERSION, ResultRecord

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
    "export_molecule_viewer",
    "OpenWFNCalculation",
    "MODEL_SCHEMA_VERSION",
    "BoundaryConditions",
    "CalculationData",
    "Provenance",
    "RESULT_SCHEMA_VERSION",
    "ResultRecord",
    "available_analyses",
    "run_analysis",
    "load",
]
