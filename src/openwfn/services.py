"""Application services shared by direct, guided, and Python interfaces."""

import numpy as np

from .analysis.basis import ao_atom_indices, overlap_matrix
from .analysis.density import density_matrix_for_kind, evaluate_density, integrate_density
from .analysis.electrostatics import electronic_esp_from_grid, nuclear_esp, point_charge_esp
from .analysis.grids import molecular_grid_points, scalar_grid
from .analysis.orbitals import frontier_orbitals
from .analysis.population import lowdin_population, mulliken_population
from .constants import BOHR_TO_ANGSTROM
from .errors import DataUnavailableError
from .exporters.cube import write_cube
from .geometry import angle, dihedral, distance
from .model import CalculationData, Molecule
from .results import ResultRecord


def _coordinates(molecule: Molecule) -> list[tuple[float, float, float]]:
    return [atom.coordinates for atom in molecule.atoms]


def geometry_distance(molecule: Molecule, atom_i: int, atom_j: int) -> ResultRecord:
    value = distance(atom_i, atom_j, _coordinates(molecule))
    return ResultRecord(
        kind="distance",
        data={"atom_i": atom_i, "atom_j": atom_j, "value": round(value, 6)},
        units={"value": "angstrom"},
        validation_status="Stable",
    )


def geometry_angle(molecule: Molecule, atom_i: int, atom_j: int, atom_k: int) -> ResultRecord:
    value = angle(atom_i, atom_j, atom_k, _coordinates(molecule))
    return ResultRecord(
        kind="angle",
        data={"atom_i": atom_i, "atom_j": atom_j, "atom_k": atom_k, "value": round(value, 6)},
        units={"value": "degree"},
        validation_status="Stable",
    )


def geometry_dihedral(
    molecule: Molecule, atom_i: int, atom_j: int, atom_k: int, atom_l: int
) -> ResultRecord:
    value = dihedral(atom_i, atom_j, atom_k, atom_l, _coordinates(molecule))
    return ResultRecord(
        kind="dihedral",
        data={
            "atom_i": atom_i,
            "atom_j": atom_j,
            "atom_k": atom_k,
            "atom_l": atom_l,
            "value": round(value, 6),
        },
        units={"value": "degree"},
        validation_status="Stable",
    )


def population_analysis(data: CalculationData, method: str) -> ResultRecord:
    if data.basis is None:
        raise DataUnavailableError("Population analysis requires Gaussian basis-set data.")
    if data.total_density is None:
        raise DataUnavailableError("Population analysis requires a total AO density matrix.")
    overlap = overlap_matrix(data.basis, data.molecule)
    mapping = ao_atom_indices(data.basis)
    if method == "mulliken":
        result = mulliken_population(data.molecule, data.total_density, overlap, mapping)
    elif method == "lowdin":
        result = lowdin_population(data.molecule, data.total_density, overlap, mapping)
    else:
        raise ValueError(f"Unknown population method: {method}")
    return ResultRecord(
        kind=f"{method}_population",
        data={
            "electron_populations": [round(value, 8) for value in result.electron_populations],
            "atomic_charges": [round(value, 8) for value in result.atomic_charges],
            "electron_count": round(result.electron_count, 8),
            "total_charge": round(result.total_charge, 8),
            "conservation_error": round(result.conservation_error, 10),
        },
        units={
            "electron_populations": "electron",
            "atomic_charges": "e",
            "electron_count": "electron",
            "total_charge": "e",
            "conservation_error": "e",
        },
        validation_status="Stable",
    )


def orbital_frontier(data: CalculationData, spin: str = "alpha") -> ResultRecord:
    if spin == "beta":
        orbitals = data.beta_orbitals
        if orbitals is None:
            raise DataUnavailableError("Beta orbitals are not available for this calculation.")
    else:
        orbitals = data.alpha_orbitals
        if orbitals is None:
            raise DataUnavailableError("Molecular orbital data are not available.")
    frontier = frontier_orbitals(orbitals)
    return ResultRecord(
        kind="frontier_orbitals",
        data={
            "spin": frontier.spin,
            "homo_number": frontier.homo_index + 1,
            "lumo_number": frontier.lumo_index + 1,
            "homo_hartree": round(frontier.homo_hartree, 10),
            "lumo_hartree": round(frontier.lumo_hartree, 10),
            "gap_hartree": round(frontier.gap_hartree, 10),
            "gap_ev": round(frontier.gap_ev, 8),
        },
        units={
            "homo_hartree": "hartree",
            "lumo_hartree": "hartree",
            "gap_hartree": "hartree",
            "gap_ev": "eV",
        },
        validation_status="Stable",
    )


def _expected_electrons(data: CalculationData, kind: str) -> float:
    total = float(sum(atom.atomic_number for atom in data.molecule.atoms) - data.molecule.charge)
    alpha = data.records.get("Number of alpha electrons")
    beta = data.records.get("Number of beta electrons")
    if kind == "total":
        return total
    if kind == "alpha" and isinstance(alpha, (int, float)):
        return float(alpha)
    if kind == "beta" and isinstance(beta, (int, float)):
        return float(beta)
    if kind == "spin" and isinstance(alpha, (int, float)) and isinstance(beta, (int, float)):
        return float(alpha - beta)
    raise DataUnavailableError(f"Expected electron count is unavailable for {kind} density.")


def density_grid(
    data: CalculationData,
    kind: str,
    spacing_bohr: float,
    padding_bohr: float,
):
    if data.basis is None:
        raise DataUnavailableError("Density analysis requires Gaussian basis-set data.")
    matrix = density_matrix_for_kind(data, kind)  # type: ignore[arg-type]
    points, origin, shape = molecular_grid_points(
        data.molecule, spacing_bohr=spacing_bohr, padding_bohr=padding_bohr
    )
    values = evaluate_density(data.molecule, data.basis, matrix, points)
    return scalar_grid(
        data.molecule, values, origin, shape, spacing_bohr, "electron/bohr^3"
    )


def density_integration(
    data: CalculationData,
    kind: str,
    spacing_bohr: float,
    padding_bohr: float,
) -> ResultRecord:
    grid = density_grid(data, kind, spacing_bohr, padding_bohr)
    result = integrate_density(grid, _expected_electrons(data, kind))
    return ResultRecord(
        kind="density_integration",
        data={
            "density_kind": kind,
            "electron_count": round(result.electron_count, 8),
            "expected_electrons": round(result.expected_electrons, 8),
            "relative_error": round(result.relative_error, 10),
            "spacing": spacing_bohr,
            "padding": padding_bohr,
        },
        units={
            "electron_count": "electron",
            "expected_electrons": "electron",
            "spacing": "bohr",
            "padding": "bohr",
        },
        validation_status="Validated" if result.relative_error < 0.005 else "Experimental",
    )


def density_cube_export(
    data: CalculationData,
    kind: str,
    spacing_bohr: float,
    padding_bohr: float,
    output_path,
    overwrite: bool,
) -> ResultRecord:
    grid = density_grid(data, kind, spacing_bohr, padding_bohr)
    write_cube(grid, data.molecule, output_path, overwrite=overwrite)
    return ResultRecord(
        kind="density_cube",
        data={
            "density_kind": kind,
            "output": str(output_path),
            "grid_points": len(grid.values),
        },
        validation_status="Validated" if kind == "total" else "Stable",
    )


def electrostatic_potential_point(
    data: CalculationData,
    coordinates_angstrom: tuple[float, float, float],
    component: str,
    spacing_bohr: float,
    padding_bohr: float,
) -> ResultRecord:
    point = np.asarray((coordinates_angstrom,), dtype=float) / BOHR_TO_ANGSTROM
    if component == "nuclear":
        value = float(nuclear_esp(data.molecule, point)[0])
        status = "Stable"
    elif component in {"mulliken", "lowdin"}:
        if data.basis is None or data.total_density is None:
            raise DataUnavailableError(
                "Atomic-charge ESP requires Gaussian basis and total-density data."
            )
        overlap = overlap_matrix(data.basis, data.molecule)
        mapping = ao_atom_indices(data.basis)
        population = (
            mulliken_population(data.molecule, data.total_density, overlap, mapping)
            if component == "mulliken"
            else lowdin_population(data.molecule, data.total_density, overlap, mapping)
        )
        centers = np.asarray([atom.coordinates for atom in data.molecule.atoms], dtype=float)
        centers /= BOHR_TO_ANGSTROM
        value = float(point_charge_esp(centers, np.asarray(population.atomic_charges), point)[0])
        status = "Stable"
    else:
        grid = density_grid(data, "total", spacing_bohr, padding_bohr)
        electronic = float(electronic_esp_from_grid(grid, point)[0])
        value = electronic
        if component == "total":
            value += float(nuclear_esp(data.molecule, point)[0])
        status = "Experimental"
    return ResultRecord(
        kind="electrostatic_potential",
        data={
            "component": component,
            "x": coordinates_angstrom[0],
            "y": coordinates_angstrom[1],
            "z": coordinates_angstrom[2],
            "value": round(value, 10),
        },
        units={"x": "angstrom", "y": "angstrom", "z": "angstrom", "value": "hartree/e"},
        validation_status=status,  # type: ignore[arg-type]
    )
