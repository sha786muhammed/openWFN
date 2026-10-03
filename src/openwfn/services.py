"""Application services shared by direct, guided, and Python interfaces."""

from typing import Literal

import numpy as np

from .analysis.basis import ao_atom_indices, bounded_ao_chunk_size, overlap_matrix
from .analysis.density import density_matrix_for_kind, evaluate_density, integrate_density
from .analysis.electrostatics import electronic_esp_from_grid, nuclear_esp, point_charge_esp
from .analysis.grids import iter_point_chunks, molecular_grid_points, scalar_grid
from .analysis.hirshfeld import HirshfeldSettings, hirshfeld_population
from .analysis.orbitals import (
    HARTREE_TO_EV,
    OCCUPATION_THRESHOLD,
    FrontierOrbitals,
    frontier_orbitals,
)
from .analysis.population import lowdin_population, mulliken_population
from .constants import BOHR_TO_ANGSTROM
from .data import StructureData
from .errors import DataUnavailableError
from .exporters.cube import write_cube
from .geometry import angle, center_of_mass, detect_bonds, dihedral, distance, molecular_formula
from .graph import build_graph
from .model import CalculationData, DensityMatrix, MolecularOrbitals, Molecule
from .orbital_services import orbital_cube_export, orbital_grid, select_orbital  # noqa: F401
from .results import ResultRecord
from .scientific import expected_electron_count, is_ghost_atom, orbital_reference_kind

POPULATION_CONSERVATION_TOLERANCE = 1e-6
LOWDIN_MIN_EIGENVALUE_TOLERANCE = 1e-8
LOWDIN_CONDITION_NUMBER_TOLERANCE = 1e10
LOWDIN_RANK_TOLERANCE = 1e-12


def _coordinates(molecule: Molecule | StructureData) -> list[tuple[float, float, float]]:
    if isinstance(molecule, StructureData):
        return list(molecule.coordinates)
    return [atom.coordinates for atom in molecule.atoms]


def _is_post_hf_method(method: str | None) -> bool:
    if not method:
        return False
    normalized = method.upper().replace("-", "").replace("_", "").replace(" ", "")
    candidates = [normalized]
    for prefix in ("RO", "R", "U"):
        if normalized.startswith(prefix):
            candidates.append(normalized[len(prefix) :])
    families = ("MP2", "MP3", "MP4", "CC", "CI", "QCI")
    return any(candidate.startswith(families) for candidate in candidates)


def _density_source_warnings(data: CalculationData, matrix: DensityMatrix) -> tuple[str, ...]:
    if matrix.source == "scf" and _is_post_hf_method(data.molecule.metadata.method):
        method = data.molecule.metadata.method or "post-HF"
        return (
            f"{method} calculation is using the SCF density because no supported post-SCF density was selected.",
        )
    return ()


def _lowdin_overlap_diagnostics(overlap: np.ndarray) -> tuple[float, float | None, bool]:
    eigenvalues = np.linalg.eigvalsh(np.asarray(overlap, dtype=float))
    minimum = float(np.min(eigenvalues))
    maximum = float(np.max(eigenvalues))
    rank_deficient = minimum <= LOWDIN_RANK_TOLERANCE
    condition_number = None if rank_deficient else maximum / minimum
    return minimum, condition_number, rank_deficient


def _density_validation_warning(result) -> str:
    if result.error_metric == "absolute":
        detail = f"absolute error {result.absolute_error:.6g} e"
    else:
        detail = f"relative error {result.relative_error:.6g}"
    return f"Density electron conservation failed: {detail} exceeds the validation tolerance."


def _frontier_payload(frontier: FrontierOrbitals) -> dict[str, object]:
    return {
        "spin": frontier.spin,
        "homo_number": frontier.homo_index + 1,
        "lumo_number": frontier.lumo_index + 1,
        "homo_hartree": round(frontier.homo_hartree, 10),
        "lumo_hartree": round(frontier.lumo_hartree, 10),
        "gap_hartree": round(frontier.gap_hartree, 10),
        "gap_ev": round(frontier.gap_ev, 8),
    }


def _frontier_payload_with_partial(
    orbitals: MolecularOrbitals,
) -> tuple[dict[str, object], bool, tuple[int, float] | None, tuple[str, ...]]:
    try:
        frontier = frontier_orbitals(orbitals)
    except ValueError as exc:
        message = str(exc)
        if not (
            message.startswith("HOMO is undefined")
            or message.startswith("LUMO is unavailable")
        ):
            raise

        occupied = [
            index
            for index, occupation in enumerate(orbitals.occupations)
            if occupation > OCCUPATION_THRESHOLD
        ]
        homo_index = (
            max(occupied, key=lambda index: orbitals.energies[index]) if occupied else None
        )
        homo_energy = orbitals.energies[homo_index] if homo_index is not None else None
        unoccupied = [
            index
            for index, occupation in enumerate(orbitals.occupations)
            if occupation <= OCCUPATION_THRESHOLD
        ]
        if homo_energy is None:
            lumo_candidates = unoccupied
        else:
            lumo_candidates = [
                index for index in unoccupied if orbitals.energies[index] > homo_energy
            ]
        lumo_index = (
            min(lumo_candidates, key=lambda index: orbitals.energies[index])
            if lumo_candidates
            else None
        )
        lumo_energy = orbitals.energies[lumo_index] if lumo_index is not None else None
        gap = (
            lumo_energy - homo_energy
            if lumo_energy is not None and homo_energy is not None
            else None
        )
        payload: dict[str, object] = {
            "spin": orbitals.spin,
            "homo_number": homo_index + 1 if homo_index is not None else None,
            "lumo_number": lumo_index + 1 if lumo_index is not None else None,
            "homo_hartree": round(homo_energy, 10) if homo_energy is not None else None,
            "lumo_hartree": round(lumo_energy, 10) if lumo_energy is not None else None,
            "gap_hartree": round(gap, 10) if gap is not None else None,
            "gap_ev": round(gap * HARTREE_TO_EV, 8) if gap is not None else None,
        }
        homo = (homo_index, homo_energy) if homo_index is not None else None
        warning = f"{orbitals.spin.capitalize()} frontier is incomplete: {message}."
        return payload, False, homo, (warning,)

    return (
        _frontier_payload(frontier),
        True,
        (frontier.homo_index, frontier.homo_hartree),
        (),
    )


def _occupation_warnings(orbitals: MolecularOrbitals) -> tuple[str, ...]:
    if orbitals.occupation_source != "electron-count filling":
        return ()
    occupied = [
        energy
        for energy, occupation in zip(orbitals.energies, orbitals.occupations)
        if occupation > OCCUPATION_THRESHOLD
    ]
    virtual = [
        energy
        for energy, occupation in zip(orbitals.energies, orbitals.occupations)
        if occupation <= OCCUPATION_THRESHOLD
    ]
    if occupied and virtual and min(virtual) <= max(occupied):
        return (
            "Orbital occupations were synthesized from electron counts, but the energy ordering is anomalous; "
            "the ordinary frontier interpretation may be unreliable.",
        )
    return ()


def molecular_summary(data: CalculationData) -> ResultRecord:
    centers = list(data.molecule.atoms)
    physical_atoms = [atom for atom in centers if not is_ghost_atom(atom)]
    ghost_count = len(centers) - len(physical_atoms)
    warnings: list[str] = []

    if physical_atoms:
        atomic_numbers = [atom.atomic_number for atom in physical_atoms]
        coordinates = [atom.coordinates for atom in physical_atoms]
        bonds = detect_bonds(atomic_numbers, coordinates)
        fragments = build_graph(len(atomic_numbers), bonds).connected_components()
        com = center_of_mass(atomic_numbers, coordinates)
        formula = molecular_formula(atomic_numbers)
        center = [round(value, 6) for value in com]
    else:
        atomic_numbers = []
        bonds = []
        fragments = ()
        formula = ""
        center = None

    if ghost_count:
        warnings.append(
            f"Structural summary excludes {ghost_count} ghost center(s) from formula, "
            "center of mass, bond inference, and fragment counting."
        )

    return ResultRecord(
        kind="summary",
        data={
            "formula": formula,
            "atoms": len(physical_atoms),
            "centers": len(centers),
            "physical_nuclei": len(physical_atoms),
            "ghost_centers": ghost_count,
            "charge": data.molecule.charge,
            "multiplicity": data.molecule.multiplicity,
            "center_of_mass": center,
            "energy_hartree": data.molecule.metadata.energy_hartree,
            "bond_count": len(bonds),
            "fragments": len(fragments),
            "bond_source": "covalent-radius heuristic",
        },
        units={"center_of_mass": "angstrom", "energy_hartree": "hartree"},
        validation_status="Stable",
        warnings=tuple(warnings),
    )


def geometry_distance(molecule: Molecule | StructureData, atom_i: int, atom_j: int) -> ResultRecord:
    value = distance(atom_i, atom_j, _coordinates(molecule))
    return ResultRecord(
        kind="distance",
        data={"atom_i": atom_i, "atom_j": atom_j, "value": round(value, 6)},
        units={"value": "angstrom"},
        validation_status="Stable",
    )


def geometry_angle(molecule: Molecule | StructureData, atom_i: int, atom_j: int, atom_k: int) -> ResultRecord:
    value = angle(atom_i, atom_j, atom_k, _coordinates(molecule))
    return ResultRecord(
        kind="angle",
        data={"atom_i": atom_i, "atom_j": atom_j, "atom_k": atom_k, "value": round(value, 6)},
        units={"value": "degree"},
        validation_status="Stable",
    )


def geometry_dihedral(
    molecule: Molecule | StructureData, atom_i: int, atom_j: int, atom_k: int, atom_l: int
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


def population_analysis(
    data: CalculationData,
    method: Literal["mulliken", "lowdin"],
) -> ResultRecord:
    if method not in {"mulliken", "lowdin"}:
        raise ValueError("population method must be 'mulliken' or 'lowdin'")
    if data.basis is None:
        raise DataUnavailableError("Population analysis requires Gaussian basis-set data.")
    if data.total_density is None:
        raise DataUnavailableError("Population analysis requires a total AO density matrix.")
    overlap = overlap_matrix(data.basis, data.molecule)
    mapping = ao_atom_indices(data.basis)
    if method == "mulliken":
        result = mulliken_population(data.molecule, data.total_density, overlap, mapping)
    else:
        result = lowdin_population(data.molecule, data.total_density, overlap, mapping)

    warnings = list(_density_source_warnings(data, data.total_density))
    partial = result.conservation_error > POPULATION_CONSERVATION_TOLERANCE
    if partial:
        warnings.append(
            "Population charge conservation failed: "
            f"error {result.conservation_error:.6g} e exceeds "
            f"tolerance {POPULATION_CONSERVATION_TOLERANCE:.6g} e."
        )

    payload: dict[str, object] = {
        "electron_populations": [round(value, 8) for value in result.electron_populations],
        "atomic_charges": [round(value, 8) for value in result.atomic_charges],
        "electron_count": round(result.electron_count, 8),
        "total_charge": round(result.total_charge, 8),
        "conservation_error": round(result.conservation_error, 10),
        "density_source": data.total_density.source,
    }
    if method == "lowdin":
        minimum, condition_number, rank_deficient = _lowdin_overlap_diagnostics(overlap)
        payload.update(
            {
                "overlap_min_eigenvalue": minimum,
                "overlap_condition_number": condition_number,
                "overlap_rank_deficient": rank_deficient,
            }
        )
        ill_conditioned = (
            rank_deficient
            or minimum < LOWDIN_MIN_EIGENVALUE_TOLERANCE
            or (
                condition_number is not None
                and condition_number > LOWDIN_CONDITION_NUMBER_TOLERANCE
            )
        )
        if ill_conditioned:
            partial = True
            warnings.append(
                "Löwdin overlap matrix is rank deficient or ill-conditioned; atomic populations may be unreliable."
            )

    return ResultRecord(
        kind=f"{method}_population",
        data=payload,
        units={
            "electron_populations": "electron",
            "atomic_charges": "e",
            "electron_count": "electron",
            "total_charge": "e",
            "conservation_error": "e",
        },
        validation_status="Experimental" if partial else "Stable",
        status="partial" if partial else "success",
        warnings=tuple(dict.fromkeys(warnings)),
    )


def hirshfeld_population_analysis(
    data: CalculationData,
    *,
    settings: HirshfeldSettings | None = None,
) -> ResultRecord:
    """Return native neutral-pro-atom Hirshfeld populations in the common result envelope."""

    result = hirshfeld_population(data, settings=settings)
    diagnostics = result.diagnostics
    quadrature = diagnostics.quadrature
    warnings = list(result.warnings)
    if data.total_density is not None:
        warnings.extend(_density_source_warnings(data, data.total_density))

    return ResultRecord(
        kind="hirshfeld_population",
        data={
            "method": result.method,
            "atoms": [
                {
                    "atom_index": atom.atom_index + 1,
                    "element": atom.symbol,
                    "effective_nuclear_charge": atom.effective_nuclear_charge,
                    "electron_population": atom.electron_population,
                    "charge": atom.net_charge,
                }
                for atom in result.atoms
            ],
            "diagnostics": {
                "expected_electrons": diagnostics.expected_electrons,
                "integrated_electrons": diagnostics.integrated_electrons,
                "electron_count_residual": diagnostics.electron_count_residual,
                "population_sum": diagnostics.population_sum,
                "population_partition_residual": diagnostics.population_partition_residual,
                "expected_molecular_charge": diagnostics.expected_molecular_charge,
                "integrated_charge": diagnostics.integrated_charge,
                "charge_closure_residual": diagnostics.charge_closure_residual,
                "negligible_promolecule_points": diagnostics.negligible_promolecule_points,
                "unresolved_promolecule_points": diagnostics.unresolved_promolecule_points,
                "passed": diagnostics.passed,
            },
            "quadrature": {
                "radial_points": quadrature.radial_points,
                "theta_points": quadrature.theta_points,
                "phi_points": quadrature.phi_points,
                "radial_extent_bohr": quadrature.radial_extent_bohr,
                "chunk_size": quadrature.chunk_size,
            },
            "reference_library": {
                "id": diagnostics.reference_library_id,
                "sha256": diagnostics.reference_library_hash,
            },
            "density_source": diagnostics.density_source,
        },
        units={
            "effective_nuclear_charge": "e",
            "electron_population": "electron",
            "charge": "e",
            "expected_electrons": "electron",
            "integrated_electrons": "electron",
            "electron_count_residual": "electron",
            "population_sum": "electron",
            "population_partition_residual": "electron",
            "expected_molecular_charge": "e",
            "integrated_charge": "e",
            "charge_closure_residual": "e",
            "radial_extent_bohr": "bohr",
        },
        validation_status=result.validation_status,
        status=result.result_status,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def orbital_frontier(
    data: CalculationData,
    spin: Literal["alpha", "beta", "all"] = "alpha",
) -> ResultRecord:
    if spin not in {"alpha", "beta", "all"}:
        raise ValueError("spin must be 'alpha', 'beta', or 'all'")
    reference_kind = orbital_reference_kind(data)
    warnings: list[str] = []

    if data.alpha_orbitals is None:
        raise DataUnavailableError("Molecular orbital data are not available.")

    if spin == "all":
        alpha_payload, alpha_complete, alpha_homo, alpha_warnings = (
            _frontier_payload_with_partial(data.alpha_orbitals)
        )
        warnings.extend(_occupation_warnings(data.alpha_orbitals))
        warnings.extend(alpha_warnings)
        beta_payload: dict[str, object] | None = None
        complete = alpha_complete
        homo_candidates: list[tuple[str, int, float]] = []
        alpha_label = "alpha" if data.beta_orbitals is not None else data.alpha_orbitals.spin
        if alpha_homo is not None:
            homo_candidates.append((alpha_label, alpha_homo[0], alpha_homo[1]))
        if data.beta_orbitals is not None:
            beta_payload, beta_complete, beta_homo, beta_warnings = (
                _frontier_payload_with_partial(data.beta_orbitals)
            )
            warnings.extend(_occupation_warnings(data.beta_orbitals))
            warnings.extend(beta_warnings)
            complete = complete and beta_complete
            if beta_homo is not None:
                homo_candidates.append(("beta", beta_homo[0], beta_homo[1]))
        if homo_candidates:
            overall_spin, overall_index, overall_energy = max(
                homo_candidates, key=lambda item: item[2]
            )
            overall_number: int | None = overall_index + 1
            overall_hartree: float | None = round(overall_energy, 10)
        else:
            overall_spin = None
            overall_number = None
            overall_hartree = None
        return ResultRecord(
            kind="frontier_orbitals",
            data={
                "spin": "all",
                "reference_kind": reference_kind,
                "occupation_source": data.alpha_orbitals.occupation_source,
                "alpha": alpha_payload,
                "beta": beta_payload,
                "overall_homo_number": overall_number,
                "overall_homo_hartree": overall_hartree,
                "overall_homo_spin": overall_spin,
            },
            units={"overall_homo_hartree": "hartree"},
            validation_status="Stable" if complete else "Experimental",
            status="success" if complete else "partial",
            warnings=tuple(dict.fromkeys(warnings)),
        )

    if spin == "beta":
        orbitals = data.beta_orbitals
        if orbitals is None:
            raise DataUnavailableError("Beta orbitals are not available for this calculation.")
    else:
        orbitals = data.alpha_orbitals
        if data.beta_orbitals is not None:
            warnings.append(
                "Unrestricted calculation contains a beta orbital channel; use spin='all' "
                "for the complete frontier view."
            )

    warnings.extend(_occupation_warnings(orbitals))
    payload, complete, _homo, partial_warnings = _frontier_payload_with_partial(orbitals)
    warnings.extend(partial_warnings)
    payload.update(
        {
            "reference_kind": reference_kind,
            "occupation_source": orbitals.occupation_source,
        }
    )
    return ResultRecord(
        kind="frontier_orbitals",
        data=payload,
        units={
            "homo_hartree": "hartree",
            "lumo_hartree": "hartree",
            "gap_hartree": "hartree",
            "gap_ev": "eV",
        },
        validation_status="Stable" if complete else "Experimental",
        status="success" if complete else "partial",
        warnings=tuple(dict.fromkeys(warnings)),
    )


def density_grid(
    data: CalculationData,
    kind: Literal["total", "alpha", "beta", "spin"],
    spacing_bohr: float,
    padding_bohr: float,
    *,
    chunk_size: int = 65536,
):
    if kind not in {"total", "alpha", "beta", "spin"}:
        raise ValueError("density kind must be 'total', 'alpha', 'beta', or 'spin'")
    if chunk_size <= 0:
        raise ValueError("chunk size must be positive")
    if data.basis is None:
        raise DataUnavailableError("Density analysis requires Gaussian basis-set data.")
    matrix = density_matrix_for_kind(data, kind)
    points, origin, shape = molecular_grid_points(
        data.molecule, spacing_bohr=spacing_bohr, padding_bohr=padding_bohr
    )
    values = np.empty(len(points), dtype=float)
    # Bound AO evaluation temporaries as well as the number of grid points.
    chunk_size = bounded_ao_chunk_size(data.basis, chunk_size)
    offset = 0
    for chunk in iter_point_chunks(points, chunk_size):
        chunk_values = evaluate_density(data.molecule, data.basis, matrix, chunk)
        stop = offset + len(chunk_values)
        values[offset:stop] = chunk_values
        offset = stop
    return scalar_grid(data.molecule, values, origin, shape, spacing_bohr, "electron/bohr^3")


def density_integration(
    data: CalculationData,
    kind: Literal["total", "alpha", "beta", "spin"],
    spacing_bohr: float,
    padding_bohr: float,
) -> ResultRecord:
    matrix = density_matrix_for_kind(data, kind)
    expectation = expected_electron_count(data, kind)
    grid = density_grid(data, kind, spacing_bohr, padding_bohr)
    result = integrate_density(grid, expectation.value)
    warnings = [*expectation.warnings, *_density_source_warnings(data, matrix)]
    if not result.passed:
        warnings.append(_density_validation_warning(result))
    return ResultRecord(
        kind="density_integration",
        data={
            "density_kind": kind,
            "electron_count": round(result.electron_count, 8),
            "expected_electrons": round(result.expected_electrons, 8),
            "absolute_error": round(result.absolute_error, 10),
            "relative_error": (
                round(result.relative_error, 10) if result.relative_error is not None else None
            ),
            "error_metric": result.error_metric,
            "expectation_source": expectation.source,
            "density_source": matrix.source,
            "spacing": spacing_bohr,
            "padding": padding_bohr,
        },
        units={
            "electron_count": "electron",
            "expected_electrons": "electron",
            "absolute_error": "electron",
            "spacing": "bohr",
            "padding": "bohr",
        },
        validation_status="Validated" if result.passed else "Experimental",
        status="success" if result.passed else "partial",
        warnings=tuple(dict.fromkeys(warnings)),
    )


def density_cube_export(
    data: CalculationData,
    kind: Literal["total", "alpha", "beta", "spin"],
    spacing_bohr: float,
    padding_bohr: float,
    output_path,
    overwrite: bool,
) -> ResultRecord:
    matrix = density_matrix_for_kind(data, kind)
    expectation = expected_electron_count(data, kind)
    grid = density_grid(data, kind, spacing_bohr, padding_bohr)
    result = integrate_density(grid, expectation.value)
    write_cube(grid, data.molecule, output_path, overwrite=overwrite)
    warnings = [*expectation.warnings, *_density_source_warnings(data, matrix)]
    if not result.passed:
        warnings.append(_density_validation_warning(result))
    return ResultRecord(
        kind="density_cube",
        data={
            "density_kind": kind,
            "output": str(output_path),
            "grid_points": len(grid.values),
            "electron_count": round(result.electron_count, 8),
            "expected_electrons": round(result.expected_electrons, 8),
            "absolute_error": round(result.absolute_error, 10),
            "relative_error": (
                round(result.relative_error, 10) if result.relative_error is not None else None
            ),
            "error_metric": result.error_metric,
            "expectation_source": expectation.source,
            "density_source": matrix.source,
        },
        units={
            "electron_count": "electron",
            "expected_electrons": "electron",
            "absolute_error": "electron",
        },
        validation_status="Validated" if result.passed else "Experimental",
        status="success" if result.passed else "partial",
        warnings=tuple(dict.fromkeys(warnings)),
    )


def electrostatic_potential_point(
    data: CalculationData,
    coordinates_angstrom: tuple[float, float, float],
    component: Literal["nuclear", "electronic", "total", "mulliken", "lowdin"],
    spacing_bohr: float,
    padding_bohr: float,
    *, method: Literal["grid", "integrals"] = "grid",
) -> ResultRecord:
    if method not in {"grid", "integrals"}:
        raise ValueError("ESP method must be grid or integrals")
    if component not in {"nuclear", "electronic", "total", "mulliken", "lowdin"}:
        raise ValueError(
            "ESP component must be 'nuclear', 'electronic', 'total', 'mulliken', or 'lowdin'"
        )
    point = np.asarray((coordinates_angstrom,), dtype=float) / BOHR_TO_ANGSTROM
    if point.shape != (1, 3) or not np.all(np.isfinite(point)):
        raise ValueError("ESP coordinates must contain three finite values in angstrom.")
    nuclear_value = None
    if component in {"nuclear", "total"}:
        nuclear_value = float(nuclear_esp(data.molecule, point)[0])
        if not np.isfinite(nuclear_value):
            raise ValueError(
                "ESP is singular at a nuclear position. Choose a point farther from the nuclei."
            )
    warnings: list[str] = []
    grid_diagnostics: dict[str, object] = {}
    density_source: str | None = None
    result_status = "success"
    if component == "nuclear":
        value = nuclear_value
        status = "Stable"
    elif component in {"mulliken", "lowdin"}:
        if data.basis is None or data.total_density is None:
            raise DataUnavailableError(
                "Atomic-charge ESP requires Gaussian basis and total-density data."
            )
        matrix = data.total_density
        density_source = matrix.source
        warnings.extend(_density_source_warnings(data, matrix))
        population = population_analysis(data, component)
        warnings.extend(population.warnings)
        result_status = population.status
        centers = np.asarray([atom.coordinates for atom in data.molecule.atoms], dtype=float)
        centers /= BOHR_TO_ANGSTROM
        value = float(point_charge_esp(centers, np.asarray(population.data["atomic_charges"]), point)[0])
        if not np.isfinite(value):
            raise ValueError(
                "Atomic-charge ESP is singular at a nuclear/atomic-charge center. "
                "Choose a point farther from the charge centers."
            )
        status = population.validation_status
    else:
        matrix = density_matrix_for_kind(data, "total")
        density_source = matrix.source
        warnings.extend(_density_source_warnings(data, matrix))
        if method == "integrals":
            from .analysis.gaussian_coulomb import electronic_potential

            if data.basis is None:
                raise DataUnavailableError("Integral ESP requires Gaussian basis data.")
            electronic_values, diagnostics = electronic_potential(
                data.molecule, data.basis, matrix, point)
            expectation = expected_electron_count(data, "total")
            electron_count = float(np.trace(np.asarray(matrix.values) @ overlap_matrix(data.basis, data.molecule)))
            error = abs(electron_count-expectation.value)
            grid_diagnostics = {**diagnostics, "method": "integrals",
                                "electron_count": electron_count,
                                "expected_electrons": expectation.value,
                                "electron_conservation_error": error}
            warnings.extend(expectation.warnings)
            if error > POPULATION_CONSERVATION_TOLERANCE or not diagnostics["quadrature_passed"]:
                result_status = "partial"
                warnings.append("Integral ESP electron conservation or auxiliary quadrature convergence failed.")
            electronic = float(electronic_values[0])
        else:
            grid = density_grid(data, "total", spacing_bohr, padding_bohr)
            expectation = expected_electron_count(data, "total")
            conservation = integrate_density(grid, expectation.value)
            grid_diagnostics = {
                "grid_electron_count": conservation.electron_count,
                "expected_electrons": expectation.value,
                "grid_electron_conservation_error": conservation.absolute_error,
                "grid_spacing_bohr": spacing_bohr,
                "grid_padding_bohr": padding_bohr,
            }
            if not conservation.passed:
                result_status = "partial"
                warnings.append(
                    "ESP density-grid electron conservation failed; refine spacing/padding. "
                    "Charge conservation alone does not establish Coulomb-quadrature convergence."
                )
            electronic = float(electronic_esp_from_grid(grid, point)[0])
        value = electronic
        if component == "total":
            value += nuclear_value
        status = "Validated" if method == "integrals" and result_status == "success" else "Experimental"
    if not np.isfinite(value):
        raise ValueError(
            "Electronic ESP quadrature is singular at a density-grid point. "
            "Choose a different evaluation point or grid spacing."
        )
    payload: dict[str, object] = {
        "component": component,
        "x": coordinates_angstrom[0],
        "y": coordinates_angstrom[1],
        "z": coordinates_angstrom[2],
        "value": round(value, 10),
        **grid_diagnostics,
    }
    if density_source is not None:
        payload["density_source"] = density_source
    return ResultRecord(
        kind="electrostatic_potential",
        data=payload,
        units={"x": "angstrom", "y": "angstrom", "z": "angstrom", "value": "hartree/e"},
        validation_status=status,  # type: ignore[arg-type]
        status=result_status,  # type: ignore[arg-type]
        warnings=tuple(dict.fromkeys(warnings)),
    )


def mayer_bond_orders(data: CalculationData, threshold: float = .05) -> ResultRecord:
    """Conventional Mayer bond orders; row sums are bonded-valence diagnostics."""
    from math import isfinite

    from .analysis.bondorder import mayer_matrix

    if not isfinite(threshold) or threshold < 0:
        raise ValueError('bond-order threshold must be finite and nonnegative')
    if data.basis is None or data.total_density is None:
        raise DataUnavailableError('Mayer analysis requires Gaussian basis and total AO density.')
    # This helper refuses absent open-shell spin density; no fabricated Q=0.
    spin = density_matrix_for_kind(data, 'spin')
    overlap = overlap_matrix(data.basis, data.molecule)
    total = np.asarray(data.total_density.values)
    matrix = mayer_matrix(total, np.asarray(spin.values), overlap,
                          ao_atom_indices(data.basis), len(data.molecule.atoms))
    population = population_analysis(data, 'mulliken')
    warnings = list(population.warnings)
    spin_count = float(np.trace(np.asarray(spin.values) @ overlap))
    expected_spin = None
    spin_error = None
    try:
        expectation = expected_electron_count(data, "spin")
        expected_spin = expectation.value
        spin_error = abs(spin_count-expected_spin)
        warnings.extend(expectation.warnings)
        if spin_error > POPULATION_CONSERVATION_TOLERANCE:
            warnings.append(f"Spin conservation failed: error {spin_error:.6g} e exceeds 1e-6 e.")
    except DataUnavailableError:
        warnings.append("Spin conservation could not be checked: authoritative spin electron count is unavailable.")
    if spin.source != data.total_density.source:
        warnings.append('Total and spin density sources differ; Mayer spin consistency is unconfirmed.')
    if _is_post_hf_method(data.molecule.metadata.method) and data.total_density.source != 'scf':
        warnings.append('Conventional Mayer index applied to a correlated density; improved correlated Mayer definitions are not implemented.')
    return ResultRecord(kind='mayer_bond_order', data={
        'convention': 'Mayer: PS products + spin QS products',
        'bond_order_matrix': matrix.tolist(),
        'pairs': [{'atom1': i+1, 'atom2': j+1, 'bond_order': float(matrix[i, j])}
                  for i in range(len(matrix)) for j in range(i+1, len(matrix))
                  if abs(matrix[i, j]) >= threshold],
        'threshold': threshold, 'bonded_valence': matrix.sum(axis=1).tolist(),
        'charge_conservation_error': population.data['conservation_error'],
        'density_source': data.total_density.source, 'spin_density_source': spin.source,
        'reference_kind': orbital_reference_kind(data),
        'spin_electron_count': spin_count, 'expected_spin_electrons': expected_spin,
        'spin_conservation_error': spin_error,
    }, units={'bond_order_matrix': 'dimensionless', 'pairs': 'dimensionless',
              'bonded_valence': 'dimensionless', 'charge_conservation_error': 'e',
              'spin_electron_count': 'electron', 'expected_spin_electrons': 'electron',
              'spin_conservation_error': 'electron'},
        validation_status='Experimental' if warnings else 'Validated', status='partial' if warnings else 'success',
        warnings=tuple(dict.fromkeys(warnings)))
