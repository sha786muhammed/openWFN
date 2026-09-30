"""Canonical heterogeneous data container for openWFN interoperability."""

from dataclasses import dataclass
from math import isfinite

from .errors import DataUnavailableError
from .model import (
    BasisSet,
    Bond,
    CalculationData,
    DensityMatrix,
    MolecularOrbitals,
    Molecule,
    Provenance,
    VolumetricGrid,
)

INTEROP_SCHEMA_VERSION = "1.0"


def _require_finite_vectors(label: str, vectors: tuple[tuple[float, float, float], ...]) -> None:
    if any(len(vector) != 3 for vector in vectors):
        raise ValueError(f"{label} must contain three-component vectors")
    if any(not isfinite(value) for vector in vectors for value in vector):
        raise ValueError(f"{label} must contain only finite values")


@dataclass(frozen=True, slots=True)
class StructureData:
    """Structure data that does not require a full molecular wavefunction."""

    coordinates: tuple[tuple[float, float, float], ...]
    atomic_numbers: tuple[int | None, ...]
    labels: tuple[str | None, ...] = ()
    bonds: tuple[Bond, ...] = ()
    charge: int | None = None
    multiplicity: int | None = None

    def __post_init__(self) -> None:
        if len(self.coordinates) != len(self.atomic_numbers):
            raise ValueError("coordinates and atomic_numbers must contain the same number of entries")
        if not self.coordinates:
            raise ValueError("structure must contain at least one coordinate")
        _require_finite_vectors("coordinates", self.coordinates)
        if self.labels and len(self.labels) != len(self.coordinates):
            raise ValueError("labels and coordinates must contain the same number of entries")
        if any(number is not None and number < 1 for number in self.atomic_numbers):
            raise ValueError("atomic numbers must be positive when known")
        if self.multiplicity is not None and self.multiplicity < 1:
            raise ValueError("multiplicity must be at least one when known")
        if any(
            bond.atom1 >= len(self.coordinates) or bond.atom2 >= len(self.coordinates)
            for bond in self.bonds
        ):
            raise ValueError("bond atom index exceeds structure atom count")


@dataclass(frozen=True, slots=True)
class PeriodicData:
    """Periodic cell information stored in ångström."""

    cell_vectors: tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ]
    periodic_axes: tuple[bool, bool, bool] = (True, True, True)

    def __post_init__(self) -> None:
        if len(self.cell_vectors) != 3 or len(self.periodic_axes) != 3:
            raise ValueError("periodic data requires exactly three cell vectors and axis flags")
        _require_finite_vectors("cell vectors", self.cell_vectors)


@dataclass(frozen=True, slots=True)
class IntegralTerm:
    """One sparse one- or two-electron integral term."""

    indices: tuple[int, ...]
    value: float

    def __post_init__(self) -> None:
        if not self.indices or any(index < 0 for index in self.indices):
            raise ValueError("integral indices must be non-negative and nonempty")
        if not isfinite(self.value):
            raise ValueError("integral value must be finite")


@dataclass(frozen=True, slots=True)
class IntegralData:
    """Sparse integral data such as FCIDUMP content."""

    n_orbitals: int | None = None
    n_electrons: int | None = None
    core_energy_hartree: float | None = None
    one_electron: tuple[IntegralTerm, ...] = ()
    two_electron: tuple[IntegralTerm, ...] = ()

    def __post_init__(self) -> None:
        if self.n_orbitals is not None and self.n_orbitals < 1:
            raise ValueError("n_orbitals must be positive when known")
        if self.n_electrons is not None and self.n_electrons < 0:
            raise ValueError("n_electrons must be non-negative when known")
        if self.core_energy_hartree is not None and not isfinite(self.core_energy_hartree):
            raise ValueError("core energy must be finite when known")


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    """Program-independent metadata retained from an imported source."""

    source_program: str | None = None
    source_program_version: str | None = None
    title: str | None = None
    energy_hartree: float | None = None

    def __post_init__(self) -> None:
        if self.energy_hartree is not None and not isfinite(self.energy_hartree):
            raise ValueError("energy_hartree must be finite when known")


@dataclass(frozen=True, slots=True)
class OpenWFNData:
    """Top-level openWFN-owned representation of one scientific input record."""

    calculation: CalculationData | None
    structure: StructureData | None
    periodic: PeriodicData | None
    grids: tuple[VolumetricGrid, ...]
    integrals: IntegralData | None
    metadata: SourceMetadata
    provenance: Provenance | None

    @property
    def molecule(self) -> Molecule:
        if self.calculation is None:
            raise DataUnavailableError("Input does not contain a molecular calculation.")
        return self.calculation.molecule

    @property
    def basis(self) -> BasisSet | None:
        return self.calculation.basis if self.calculation is not None else None

    @property
    def alpha_orbitals(self) -> MolecularOrbitals | None:
        return self.calculation.alpha_orbitals if self.calculation is not None else None

    @property
    def beta_orbitals(self) -> MolecularOrbitals | None:
        return self.calculation.beta_orbitals if self.calculation is not None else None

    @property
    def total_density(self) -> DensityMatrix | None:
        return self.calculation.total_density if self.calculation is not None else None

    @property
    def spin_density(self) -> DensityMatrix | None:
        return self.calculation.spin_density if self.calculation is not None else None

    @property
    def records(self) -> dict[str, object]:
        """Expose legacy calculation records for molecular inputs.

        This compatibility view lets existing scientific helpers accept the
        new canonical container without changing the authoritative
        ``CalculationData`` object stored in ``calculation``.
        """

        return self.calculation.records if self.calculation is not None else {}


def wrap_calculation(data: CalculationData) -> OpenWFNData:
    """Wrap existing molecular data without copying its large scientific arrays."""

    molecule = data.molecule
    structure = StructureData(
        coordinates=tuple(atom.coordinates for atom in molecule.atoms),
        atomic_numbers=tuple(atom.atomic_number for atom in molecule.atoms),
        labels=tuple(None for _ in molecule.atoms),
        bonds=molecule.bonds,
        charge=molecule.charge,
        multiplicity=molecule.multiplicity,
    )
    metadata = SourceMetadata(
        source_program=molecule.metadata.source_program,
        source_program_version=molecule.metadata.source_program_version,
        energy_hartree=molecule.metadata.energy_hartree,
    )
    return OpenWFNData(
        calculation=data,
        structure=structure,
        periodic=None,
        grids=(),
        integrals=None,
        metadata=metadata,
        provenance=molecule.provenance,
    )
