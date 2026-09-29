"""openWFN-owned canonical container for heterogeneous scientific inputs."""

from dataclasses import dataclass
from math import isfinite

from .errors import DataUnavailableError
from .model import Bond, CalculationData, Provenance, VolumetricGrid

INTEROP_SCHEMA_VERSION = "1.0"


def _require_vector3(label: str, values: tuple[float, ...]) -> None:
    if len(values) != 3:
        raise ValueError(f"{label} must contain exactly three values")
    if any(not isfinite(value) for value in values):
        raise ValueError(f"{label} must contain only finite values")


@dataclass(frozen=True, slots=True)
class StructureData:
    """Program-neutral molecular or structural coordinates in ångström."""

    coordinates: tuple[tuple[float, float, float], ...]
    atomic_numbers: tuple[int | None, ...]
    labels: tuple[str | None, ...] = ()
    bonds: tuple[Bond, ...] = ()
    charge: int | None = None
    multiplicity: int | None = None

    def __post_init__(self) -> None:
        if len(self.atomic_numbers) != len(self.coordinates):
            raise ValueError("atomic_numbers must match coordinates")
        if self.labels and len(self.labels) != len(self.coordinates):
            raise ValueError("labels must match coordinates")
        for coordinate in self.coordinates:
            _require_vector3("coordinates", coordinate)
        if any(number is not None and number < 1 for number in self.atomic_numbers):
            raise ValueError("atomic_numbers must be positive when known")
        if self.multiplicity is not None and self.multiplicity < 1:
            raise ValueError("multiplicity must be at least one when known")
        atom_count = len(self.coordinates)
        if any(bond.atom1 >= atom_count or bond.atom2 >= atom_count for bond in self.bonds):
            raise ValueError("bond atom index exceeds structure atom count")


@dataclass(frozen=True, slots=True)
class PeriodicData:
    """Periodic cell metadata stored independently from molecular calculations."""

    cell_vectors: tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ]
    periodic_axes: tuple[bool, bool, bool] = (True, True, True)

    def __post_init__(self) -> None:
        if len(self.cell_vectors) != 3:
            raise ValueError("periodic data must contain exactly three cell vectors")
        for vector in self.cell_vectors:
            _require_vector3("cell vector", vector)
        if len(self.periodic_axes) != 3:
            raise ValueError("periodic_axes must contain exactly three values")


@dataclass(frozen=True, slots=True)
class IntegralTerm:
    """One indexed electronic-integral value."""

    indices: tuple[int, ...]
    value: float

    def __post_init__(self) -> None:
        if not self.indices or any(index < 0 for index in self.indices):
            raise ValueError("integral indices must be non-empty and non-negative")
        if not isfinite(self.value):
            raise ValueError("integral value must be finite")


@dataclass(frozen=True, slots=True)
class IntegralData:
    """Integral payload such as data imported from FCIDUMP."""

    n_orbitals: int | None = None
    n_electrons: int | None = None
    core_energy_hartree: float | None = None
    one_electron: tuple[IntegralTerm, ...] = ()
    two_electron: tuple[IntegralTerm, ...] = ()

    def __post_init__(self) -> None:
        if self.n_orbitals is not None and self.n_orbitals < 0:
            raise ValueError("n_orbitals must be non-negative")
        if self.n_electrons is not None and self.n_electrons < 0:
            raise ValueError("n_electrons must be non-negative")
        if self.core_energy_hartree is not None and not isfinite(self.core_energy_hartree):
            raise ValueError("core_energy_hartree must be finite")


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    """Source-program metadata that can exist without a full molecular calculation."""

    source_program: str | None = None
    source_program_version: str | None = None
    title: str | None = None
    energy_hartree: float | None = None

    def __post_init__(self) -> None:
        if self.energy_hartree is not None and not isfinite(self.energy_hartree):
            raise ValueError("energy_hartree must be finite")


@dataclass(frozen=True, slots=True)
class OpenWFNData:
    """Top-level canonical container consumed by capability-aware interfaces."""

    calculation: CalculationData | None
    structure: StructureData | None
    periodic: PeriodicData | None
    grids: tuple[VolumetricGrid, ...]
    integrals: IntegralData | None
    metadata: SourceMetadata
    provenance: Provenance

    @property
    def molecule(self):
        if self.calculation is None:
            raise DataUnavailableError("Input does not contain a molecular calculation.")
        return self.calculation.molecule

    @property
    def basis(self):
        return self.calculation.basis if self.calculation is not None else None

    @property
    def alpha_orbitals(self):
        return self.calculation.alpha_orbitals if self.calculation is not None else None

    @property
    def beta_orbitals(self):
        return self.calculation.beta_orbitals if self.calculation is not None else None

    @property
    def total_density(self):
        return self.calculation.total_density if self.calculation is not None else None

    @property
    def spin_density(self):
        return self.calculation.spin_density if self.calculation is not None else None


def wrap_calculation(data: CalculationData) -> OpenWFNData:
    """Wrap an existing molecular calculation without copying scientific arrays."""

    molecule = data.molecule
    provenance = molecule.provenance
    if provenance is None:
        raise DataUnavailableError("Calculation does not include source provenance.")
    structure = StructureData(
        coordinates=tuple(atom.coordinates for atom in molecule.atoms),
        atomic_numbers=tuple(atom.atomic_number for atom in molecule.atoms),
        bonds=molecule.bonds,
        charge=molecule.charge,
        multiplicity=molecule.multiplicity,
    )
    source = molecule.metadata
    metadata = SourceMetadata(
        source_program=source.source_program,
        source_program_version=source.source_program_version,
        energy_hartree=source.energy_hartree,
    )
    return OpenWFNData(
        calculation=data,
        structure=structure,
        periodic=None,
        grids=(),
        integrals=None,
        metadata=metadata,
        provenance=provenance,
    )
