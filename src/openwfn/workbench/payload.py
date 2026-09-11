"""Versioned data contract embedded in standalone workbench files."""

import json
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .. import __version__
from ..analysis.basis import ao_atom_indices, overlap_matrix
from ..analysis.electrostatics import point_charge_esp
from ..analysis.grids import molecular_grid_points, scalar_grid
from ..analysis.orbitals import evaluate_orbital, frontier_orbitals
from ..analysis.population import mulliken_population
from ..constants import BOHR_TO_ANGSTROM, Z_TO_SYMBOL
from ..exporters.cube import format_cube
from ..model import CalculationData
from ..services import density_grid, orbital_frontier, population_analysis


@dataclass(frozen=True, slots=True)
class WorkbenchPayload:
    schema_version: str
    openwfn_version: str
    molecule: dict[str, Any]
    properties: dict[str, Any]
    fields: list[dict[str, Any]]
    provenance: dict[str, Any]

    @classmethod
    def from_calculation(
        cls, data: CalculationData, *, include_fields: bool = False
    ) -> "WorkbenchPayload":
        molecule = {
            "atoms": [
                {
                    "index": index,
                    "atomic_number": atom.atomic_number,
                    "symbol": Z_TO_SYMBOL.get(atom.atomic_number, "X"),
                    "coordinates": list(atom.coordinates),
                    "coordinate_unit": atom.coordinate_unit,
                }
                for index, atom in enumerate(data.molecule.atoms, start=1)
            ],
            "charge": data.molecule.charge,
            "multiplicity": data.molecule.multiplicity,
        }
        properties: dict[str, Any] = {
            "calculation": {
                "source_program": data.molecule.metadata.source_program,
                "method": data.molecule.metadata.method,
                "basis": data.molecule.metadata.basis,
                "energy_hartree": data.molecule.metadata.energy_hartree,
            }
        }
        for name, operation in (
            ("frontier", lambda: orbital_frontier(data)),
            ("mulliken", lambda: population_analysis(data, "mulliken")),
            ("lowdin", lambda: population_analysis(data, "lowdin")),
        ):
            try:
                result = operation()
                properties[name] = {
                    **result.data,
                    "units": result.units,
                    "validation_status": result.validation_status,
                }
            except Exception as exc:
                properties[name] = {"status": "Unavailable", "error": str(exc)}
        provenance = data.molecule.provenance
        fields: list[dict[str, Any]] = []
        if include_fields and data.basis is not None:
            spacing = 0.3
            padding = 3.0
            if data.total_density is not None:
                density = density_grid(data, "total", spacing, padding)
                fields.append({
                    "id": "density-total", "name": "Total electron density", "workspace": "density",
                    "cube": format_cube(density, data.molecule), "isovalue": 0.02,
                    "units": "electron/bohr^3", "validation_status": "Stable",
                    "grid": {"spacing_bohr": spacing, "padding_bohr": padding},
                })
            if data.alpha_orbitals is not None:
                frontier = frontier_orbitals(data.alpha_orbitals)
                points, origin, shape = molecular_grid_points(
                    data.molecule, spacing_bohr=spacing, padding_bohr=padding
                )
                values = evaluate_orbital(
                    data.molecule, data.basis, data.alpha_orbitals, frontier.homo_index, points
                )
                orbital_grid = scalar_grid(
                    data.molecule, values, origin, shape, spacing, "wavefunction"
                )
                fields.append({
                    "id": "orbital-homo", "name": "HOMO", "workspace": "orbitals",
                    "cube": format_cube(orbital_grid, data.molecule), "isovalue": 0.03,
                    "units": "wavefunction", "validation_status": "Stable", "signed": True,
                    "grid": {"spacing_bohr": spacing, "padding_bohr": padding},
                })
            if data.total_density is not None:
                overlap = overlap_matrix(data.basis, data.molecule)
                population = mulliken_population(
                    data.molecule, data.total_density, overlap, ao_atom_indices(data.basis)
                )
                points, origin, shape = molecular_grid_points(
                    data.molecule, spacing_bohr=spacing, padding_bohr=padding
                )
                centers = np.asarray([atom.coordinates for atom in data.molecule.atoms]) / BOHR_TO_ANGSTROM
                values = point_charge_esp(
                    centers, np.asarray(population.atomic_charges), points,
                    singularity_value=0.0, singularity_tolerance=1e-8,
                )
                esp_grid = scalar_grid(data.molecule, values, origin, shape, spacing, "hartree/e")
                fields.append({
                    "id": "esp-mulliken", "name": "Mulliken ESP", "workspace": "esp",
                    "cube": format_cube(esp_grid, data.molecule), "isovalue": 0.02,
                    "units": "hartree/e", "validation_status": "Stable", "signed": True,
                    "grid": {"spacing_bohr": spacing, "padding_bohr": padding},
                })
        return cls(
            schema_version="1.0",
            openwfn_version=__version__,
            molecule=molecule,
            properties=properties,
            fields=fields,
            provenance={
                "source_path": provenance.source_path if provenance else "Unavailable",
                "sha256": provenance.sha256 if provenance else "Unavailable",
                "parser": provenance.parser if provenance else "Unavailable",
                "warnings": list(provenance.warnings) if provenance else [],
            },
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)
