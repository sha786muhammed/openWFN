"""Native Hirshfeld stockholder population analysis."""

from dataclasses import dataclass, field

import numpy as np

from openwfn.constants import BOHR_TO_ANGSTROM
from openwfn.errors import DataUnavailableError, ValidationError
from openwfn.model import CalculationData
from openwfn.scientific import effective_nuclear_charge, expected_electron_count, is_ghost_atom

from .atom_quadrature import AtomQuadratureSettings, iter_atom_centered_chunks
from .density import evaluate_density
from .hirshfeld_reference import HirshfeldReferenceLibrary, ReferenceDensity, load_hirshfeld_reference_library


@dataclass(frozen=True, slots=True)
class HirshfeldSettings:
    """Numerical controls for native Hirshfeld population analysis."""

    quadrature: AtomQuadratureSettings = field(default_factory=AtomQuadratureSettings)
    molecular_density_screen: float = 1.0e-12
    promolecule_floor: float = 1.0e-14
    population_partition_tolerance: float = 1.0e-8
    electron_closure_tolerance: float = 5.0e-3
    charge_closure_tolerance: float = 5.0e-3
    negative_density_tolerance: float = 1.0e-10

    def __post_init__(self) -> None:
        positive = {
            "molecular_density_screen": self.molecular_density_screen,
            "promolecule_floor": self.promolecule_floor,
            "population_partition_tolerance": self.population_partition_tolerance,
            "electron_closure_tolerance": self.electron_closure_tolerance,
            "charge_closure_tolerance": self.charge_closure_tolerance,
            "negative_density_tolerance": self.negative_density_tolerance,
        }
        for name, value in positive.items():
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and positive")
        if self.promolecule_floor >= self.molecular_density_screen:
            raise ValueError("promolecule_floor must be smaller than molecular_density_screen")


@dataclass(frozen=True, slots=True)
class HirshfeldAtomResult:
    """One atom's stockholder population and net charge."""

    atom_index: int
    symbol: str
    effective_nuclear_charge: float
    electron_population: float
    net_charge: float


@dataclass(frozen=True, slots=True)
class HirshfeldDiagnostics:
    """Numerical closure and provenance diagnostics for one Hirshfeld calculation."""

    expected_electrons: float
    integrated_electrons: float
    electron_count_residual: float
    population_sum: float
    population_partition_residual: float
    expected_molecular_charge: float
    integrated_charge: float
    charge_closure_residual: float
    negligible_promolecule_points: int
    unresolved_promolecule_points: int
    quadrature: AtomQuadratureSettings
    reference_library_id: str
    reference_library_hash: str
    density_source: str | None
    passed: bool


@dataclass(frozen=True, slots=True)
class HirshfeldResult:
    """Typed native Hirshfeld result independent of presentation layers."""

    method: str
    atoms: tuple[HirshfeldAtomResult, ...]
    diagnostics: HirshfeldDiagnostics
    warnings: tuple[str, ...]
    result_status: str
    validation_status: str = "Experimental"


def _validated_references(
    data: CalculationData,
    library: HirshfeldReferenceLibrary,
) -> tuple[tuple[ReferenceDensity, ...], np.ndarray]:
    if data.basis is None:
        raise DataUnavailableError("Hirshfeld analysis requires a molecular basis set.")
    if data.total_density is None:
        raise DataUnavailableError("Hirshfeld analysis requires a total density matrix.")
    if data.total_density.kind != "total":
        raise ValidationError("Hirshfeld analysis requires the total molecular density channel.")
    if data.basis.ecp_metadata:
        raise ValidationError(
            "Hirshfeld analysis does not support ECP calculations without a validated reference-density convention."
        )

    by_atomic_number = {reference.atomic_number: reference for reference in library.references.values()}
    references: list[ReferenceDensity] = []
    nuclear_charges: list[float] = []
    for atom_index, atom in enumerate(data.molecule.atoms):
        if is_ghost_atom(atom):
            raise ValidationError(
                f"Hirshfeld analysis does not support ghost center at atom index {atom_index}."
            )
        charge = effective_nuclear_charge(atom)
        if abs(charge - float(atom.atomic_number)) > 1.0e-10:
            raise ValidationError(
                "Hirshfeld analysis found an effective nuclear charge that differs from the "
                f"all-electron atomic number at atom index {atom_index}; ECP/reference treatment is ambiguous."
            )
        try:
            reference = by_atomic_number[atom.atomic_number]
        except KeyError as exc:
            supported = ", ".join(library.supported_elements)
            raise ValidationError(
                "Unsupported Hirshfeld reference element with atomic number "
                f"{atom.atomic_number}. Supported elements: {supported}."
            ) from exc
        references.append(reference)
        nuclear_charges.append(charge)

    return tuple(references), np.asarray(nuclear_charges, dtype=float)


def _reference_density_at_points(
    reference: ReferenceDensity,
    center_bohr: np.ndarray,
    points_bohr: np.ndarray,
) -> np.ndarray:
    radius = np.linalg.norm(points_bohr - center_bohr, axis=1)
    return reference.evaluate(radius)


def hirshfeld_population(
    data: CalculationData,
    *,
    settings: HirshfeldSettings | None = None,
    library: HirshfeldReferenceLibrary | None = None,
) -> HirshfeldResult:
    """Compute neutral-pro-atom Hirshfeld populations from the total AO density.

    Final charges are never renormalized to force molecular charge closure. Failed
    closure or promolecular-denominator gates are preserved as partial results.
    """

    controls = HirshfeldSettings() if settings is None else settings
    references_library = load_hirshfeld_reference_library() if library is None else library
    references, nuclear_charges = _validated_references(data, references_library)
    assert data.basis is not None
    assert data.total_density is not None

    expectation = expected_electron_count(data, "total")
    centers_bohr = (
        np.asarray([atom.coordinates for atom in data.molecule.atoms], dtype=float)
        / BOHR_TO_ANGSTROM
    )
    populations = np.zeros(len(data.molecule.atoms), dtype=float)
    integrated_electrons = 0.0
    negligible_points = 0
    unresolved_points = 0

    for chunk in iter_atom_centered_chunks(data.molecule, controls.quadrature):
        molecular_density = np.asarray(
            evaluate_density(
                data.molecule,
                data.basis,
                data.total_density,
                chunk.points_bohr,
            ),
            dtype=float,
        )
        if not np.all(np.isfinite(molecular_density)):
            raise ValidationError("Hirshfeld molecular density evaluation produced non-finite values.")
        minimum_density = float(np.min(molecular_density))
        if minimum_density < -controls.negative_density_tolerance:
            raise ValidationError(
                "Hirshfeld molecular density evaluation produced materially negative density "
                f"({minimum_density:.6g} electron/bohr^3)."
            )
        molecular_density = np.maximum(molecular_density, 0.0)
        weighted_density = molecular_density * chunk.integration_weights
        integrated_electrons += float(np.sum(weighted_density))

        promolecule = np.zeros(molecular_density.shape, dtype=float)
        for atom_index, reference in enumerate(references):
            promolecule += _reference_density_at_points(
                reference,
                centers_bohr[atom_index],
                chunk.points_bohr,
            )

        active = promolecule > controls.promolecule_floor
        negligible = (~active) & (molecular_density <= controls.molecular_density_screen)
        unresolved = (~active) & (molecular_density > controls.molecular_density_screen)
        negligible_points += int(np.count_nonzero(negligible))
        unresolved_points += int(np.count_nonzero(unresolved))

        if np.any(active):
            for atom_index, reference in enumerate(references):
                pro_atom = _reference_density_at_points(
                    reference,
                    centers_bohr[atom_index],
                    chunk.points_bohr,
                )
                stockholder = np.zeros(promolecule.shape, dtype=float)
                stockholder[active] = pro_atom[active] / promolecule[active]
                populations[atom_index] += float(np.dot(weighted_density, stockholder))

    population_sum = float(np.sum(populations))
    electron_residual = abs(integrated_electrons - expectation.value)
    population_residual = abs(population_sum - integrated_electrons)
    atomic_charges = nuclear_charges - populations
    integrated_charge = float(np.sum(atomic_charges))
    expected_charge = float(data.molecule.charge)
    charge_residual = abs(integrated_charge - expected_charge)

    passed = (
        unresolved_points == 0
        and electron_residual <= controls.electron_closure_tolerance
        and population_residual <= controls.population_partition_tolerance
        and charge_residual <= controls.charge_closure_tolerance
    )

    warnings = list(expectation.warnings)
    if unresolved_points:
        warnings.append(
            "Molecular density was non-negligible at points where the promolecular density was below the configured floor."
        )
    if electron_residual > controls.electron_closure_tolerance:
        warnings.append("Integrated molecular electron count failed the Hirshfeld closure tolerance.")
    if population_residual > controls.population_partition_tolerance:
        warnings.append("Hirshfeld atomic populations failed the stockholder partition closure tolerance.")
    if charge_residual > controls.charge_closure_tolerance:
        warnings.append("Hirshfeld atomic charges failed molecular charge closure; charges were not renormalized.")

    atoms = tuple(
        HirshfeldAtomResult(
            atom_index=atom_index,
            symbol=references[atom_index].symbol,
            effective_nuclear_charge=float(nuclear_charges[atom_index]),
            electron_population=float(populations[atom_index]),
            net_charge=float(atomic_charges[atom_index]),
        )
        for atom_index in range(len(populations))
    )
    diagnostics = HirshfeldDiagnostics(
        expected_electrons=float(expectation.value),
        integrated_electrons=integrated_electrons,
        electron_count_residual=electron_residual,
        population_sum=population_sum,
        population_partition_residual=population_residual,
        expected_molecular_charge=expected_charge,
        integrated_charge=integrated_charge,
        charge_closure_residual=charge_residual,
        negligible_promolecule_points=negligible_points,
        unresolved_promolecule_points=unresolved_points,
        quadrature=controls.quadrature,
        reference_library_id=references_library.library_id,
        reference_library_hash=references_library.library_sha256,
        density_source=data.total_density.source,
        passed=passed,
    )
    return HirshfeldResult(
        method="Hirshfeld",
        atoms=atoms,
        diagnostics=diagnostics,
        warnings=tuple(warnings),
        result_status="success" if passed else "partial",
    )
