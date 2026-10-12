"""Versioned data contract embedded in standalone workbench files."""

import json
from dataclasses import asdict, dataclass
from math import prod
from typing import Any

import numpy as np

from .. import __version__
from ..analysis.density import integrate_density
from ..analysis.electrostatics import point_charge_esp
from ..analysis.grids import iter_molecular_grid_chunks, molecular_grid_layout, scalar_grid
from ..analysis.registry import run_analysis_safe
from ..constants import BOHR_TO_ANGSTROM, Z_TO_SYMBOL
from ..exporters.cube import format_cube
from ..model import CalculationData
from ..scientific import expected_electron_count, is_ghost_atom
from ..services import density_grid, orbital_frontier, orbital_grid, population_analysis


def _result_property(result) -> dict[str, Any]:
    if result.status == "failed":
        return {
            "status": "Unavailable",
            "validation_status": result.validation_status,
            "error": result.error.message if result.error else "Analysis unavailable",
            "warnings": list(result.warnings),
        }
    return {
        **result.data,
        "units": result.units,
        "validation_status": result.validation_status,
        "status": result.status,
        "warnings": list(result.warnings),
    }


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
                    "nuclear_charge": atom.nuclear_charge,
                    "is_ghost": is_ghost_atom(atom),
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
                    "status": result.status,
                    "warnings": list(result.warnings),
                }
            except Exception as exc:
                properties[name] = {"status": "Unavailable", "error": str(exc)}

        if "vibrations" in data.records:
            vibrations = run_analysis_safe(data, "vibrations")
            properties["vibrations"] = _result_property(vibrations)
            for analysis in ("ir-spectrum", "raman-spectrum"):
                properties[analysis] = _result_property(run_analysis_safe(data, analysis))
            if vibrations.status != "failed" and vibrations.data.get("displacements_available"):
                normal_modes = []
                for mode in range(1, int(vibrations.data.get("mode_count", 0)) + 1):
                    result = run_analysis_safe(data, "normal-mode", mode=mode)
                    if result.status != "failed":
                        normal_modes.append(result.data)
                properties["normal_modes"] = {
                    "available": bool(normal_modes),
                    "modes": normal_modes,
                }
            else:
                properties["normal_modes"] = {
                    "available": False,
                    "modes": [],
                    "message": "Normal-mode displacement vectors are unavailable for this source file.",
                }

        if "excited_states" in data.records:
            properties["excited-states"] = _result_property(
                run_analysis_safe(data, "excited-states")
            )
            properties["uvvis-spectrum"] = _result_property(
                run_analysis_safe(data, "uvvis-spectrum")
            )
            properties["transition-dipoles"] = _result_property(
                run_analysis_safe(data, "transition-dipoles")
            )

        provenance = data.molecule.provenance
        fields: list[dict[str, Any]] = []
        if include_fields and data.basis is not None:
            spacing = 0.3
            padding = 3.0
            if data.total_density is not None:
                density = density_grid(data, "total", spacing, padding)
                integral = integrate_density(density, expected_electron_count(data, "total").value)
                density_warnings = [] if integral.passed else ["Density electron conservation failed on the embedded grid."]
                fields.append({
                    "id": "density-total", "name": "Total electron density", "workspace": "density",
                    "cube": format_cube(density, data.molecule), "isovalue": 0.02,
                    "units": "electron/bohr^3",
                    "validation_status": "Validated" if integral.passed else "Experimental",
                    "status": "success" if integral.passed else "partial",
                    "warnings": density_warnings,
                    "grid": {"spacing_bohr": spacing, "padding_bohr": padding},
                })
                del density
            homo_number = properties["frontier"].get("homo_number")
            if data.alpha_orbitals is not None and homo_number is not None:
                orbital_field = orbital_grid(data, homo_number, "alpha", spacing, padding)
                fields.append({
                    "id": "orbital-homo", "name": "HOMO", "workspace": "orbitals",
                    "cube": format_cube(orbital_field, data.molecule, comment="units: wavefunction"), "isovalue": 0.03,
                    "units": "wavefunction", "validation_status": "Stable", "signed": True,
                    "status": properties["frontier"]["status"],
                    "warnings": properties["frontier"]["warnings"],
                    "grid": {"spacing_bohr": spacing, "padding_bohr": padding},
                })
                del orbital_field
            if data.total_density is not None and "atomic_charges" in properties["mulliken"]:
                population = properties["mulliken"]
                origin, shape = molecular_grid_layout(
                    data.molecule, spacing_bohr=spacing, padding_bohr=padding
                )
                centers = np.asarray([atom.coordinates for atom in data.molecule.atoms]) / BOHR_TO_ANGSTROM
                values = np.empty(prod(shape))
                offset = 0
                for chunk in iter_molecular_grid_chunks(data.molecule, spacing_bohr=spacing,
                        padding_bohr=padding, chunk_size=min(65536, max(1, 1_000_000 // len(centers)))):
                    block = point_charge_esp(
                        centers, np.asarray(population["atomic_charges"]), chunk,
                        singularity_value=0.0, singularity_tolerance=1e-8,
                    )
                    values[offset:offset + len(block)] = block
                    offset += len(block)
                esp_grid = scalar_grid(data.molecule, values, origin, shape, spacing, "hartree/e")
                fields.append({
                    "id": "esp-mulliken", "name": "Mulliken ESP", "workspace": "esp",
                    "cube": format_cube(esp_grid, data.molecule), "isovalue": 0.02,
                    "units": "hartree/e", "validation_status": population["validation_status"], "signed": True,
                    "status": population["status"], "warnings": population["warnings"],
                    "grid": {"spacing_bohr": spacing, "padding_bohr": padding},
                })
                del esp_grid, values
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
