"""Typed scientific domain objects used across openWFN."""

from dataclasses import dataclass, field
from math import prod
from typing import Any, Literal

MODEL_SCHEMA_VERSION = "2.0"


@dataclass(frozen=True, slots=True)
class Atom:
    """An atom with Cartesian coordinates in ångström."""

    atomic_number: int
    coordinates: tuple[float, float, float]
    coordinate_unit: Literal["angstrom"] = field(default="angstrom", init=False)

    def __post_init__(self) -> None:
        if self.atomic_number < 1:
            raise ValueError("atomic number must be positive")
        if len(self.coordinates) != 3:
            raise ValueError("coordinates must contain exactly three values")


@dataclass(frozen=True, slots=True)
class CalculationMetadata:
    """Program and method metadata retained from the source calculation."""

    source_program: str
    route: str | None = None
    method: str | None = None
    basis: str | None = None
    energy_hartree: float | None = None
    terminated_normally: bool | None = None


@dataclass(frozen=True, slots=True)
class Provenance:
    """Traceability record for parsed or generated scientific data."""

    source_path: str
    sha256: str
    parser: str
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.sha256) != 64 or any(c not in "0123456789abcdefABCDEF" for c in self.sha256):
            raise ValueError("sha256 must be a 64-character SHA-256 checksum")


@dataclass(frozen=True, order=True, slots=True)
class Bond:
    """A bond between zero-based atom indices."""

    atom1: int
    atom2: int
    order: int = 1

    def __post_init__(self) -> None:
        if self.atom1 < 0 or self.atom2 < 0 or self.atom1 == self.atom2:
            raise ValueError("bond atom indices must be distinct and non-negative")
        if self.order < 1:
            raise ValueError("bond order must be positive")


@dataclass(frozen=True, slots=True)
class BoundaryConditions:
    """Boundary conditions attached to a molecular system."""

    kind: Literal["isolated"] = "isolated"

    def __post_init__(self) -> None:
        if self.kind != "isolated":
            raise ValueError("periodic boundary conditions are not supported by the v2 foundation")


@dataclass(frozen=True, slots=True)
class Molecule:
    """Molecular identity, geometry, charge, spin, and calculation metadata."""

    atoms: tuple[Atom, ...]
    charge: int
    multiplicity: int
    metadata: CalculationMetadata
    provenance: Provenance | None = None
    bonds: tuple[Bond, ...] = ()
    boundary_conditions: BoundaryConditions = field(default_factory=BoundaryConditions)

    def __post_init__(self) -> None:
        if self.multiplicity < 1:
            raise ValueError("multiplicity must be at least one")
        if not self.atoms:
            raise ValueError("molecule must contain at least one atom")
        if any(bond.atom1 >= len(self.atoms) or bond.atom2 >= len(self.atoms) for bond in self.bonds):
            raise ValueError("bond atom index exceeds molecule atom count")


@dataclass(frozen=True, slots=True)
class BasisShell:
    """One contracted Gaussian shell centered on an atom."""

    atom_index: int
    angular_momentum: int
    exponents: tuple[float, ...]
    coefficients: tuple[float, ...]
    pure: bool = False
    p_coefficients: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        if self.atom_index < 0:
            raise ValueError("atom index must be non-negative")
        if self.angular_momentum < -1:
            raise ValueError("angular momentum is invalid")
        if not self.exponents or len(self.exponents) != len(self.coefficients):
            raise ValueError("primitive exponents and coefficients must have matching nonzero lengths")
        if self.p_coefficients is not None and len(self.p_coefficients) != len(self.exponents):
            raise ValueError("primitive p coefficients must match primitive exponents")

    @property
    def n_functions(self) -> int:
        if self.angular_momentum == -1:
            return 4
        if self.pure and self.angular_momentum >= 2:
            return 2 * self.angular_momentum + 1
        momentum = self.angular_momentum
        return (momentum + 1) * (momentum + 2) // 2


@dataclass(frozen=True, slots=True)
class BasisSet:
    """Ordered basis shells in source-program function order."""

    shells: tuple[BasisShell, ...]
    name: str | None = None
    ecp_metadata: tuple[tuple[str, str], ...] = ()

    @property
    def n_functions(self) -> int:
        return sum(shell.n_functions for shell in self.shells)


@dataclass(frozen=True, slots=True)
class MolecularOrbitals:
    """One spin channel of molecular-orbital data."""

    energies: tuple[float, ...]
    coefficients: tuple[tuple[float, ...], ...]
    occupations: tuple[float, ...]
    spin: Literal["restricted", "alpha", "beta"] = "restricted"
    energy_unit: Literal["hartree"] = field(default="hartree", init=False)

    def __post_init__(self) -> None:
        n_orbitals = len(self.energies)
        if len(self.occupations) != n_orbitals:
            raise ValueError("occupations must match orbital energies")
        if not self.coefficients or any(len(row) != n_orbitals for row in self.coefficients):
            raise ValueError("coefficient matrix columns must match orbital energies")


@dataclass(frozen=True, slots=True)
class DensityMatrix:
    """A square atomic-orbital density matrix."""

    values: tuple[tuple[float, ...], ...]
    kind: Literal["total", "alpha", "beta", "spin"]
    value_unit: Literal["electron"] = field(default="electron", init=False)

    def __post_init__(self) -> None:
        size = len(self.values)
        if size == 0 or any(len(row) != size for row in self.values):
            raise ValueError("density matrix must be square and nonempty")


@dataclass(frozen=True, slots=True)
class VolumetricGrid:
    """A regular three-dimensional scalar grid."""

    origin: tuple[float, float, float]
    axes: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]
    shape: tuple[int, int, int]
    values: tuple[float, ...]
    value_unit: str
    coordinate_unit: Literal["angstrom"] = field(default="angstrom", init=False)

    def __post_init__(self) -> None:
        if any(size < 1 for size in self.shape):
            raise ValueError("grid shape values must be positive")
        if len(self.values) != prod(self.shape):
            raise ValueError("grid values count must equal the product of grid shape")


@dataclass(frozen=True, slots=True)
class CalculationData:
    """Unified parsed calculation consumed by analyses and interfaces."""

    molecule: Molecule
    basis: BasisSet | None = None
    alpha_orbitals: MolecularOrbitals | None = None
    beta_orbitals: MolecularOrbitals | None = None
    total_density: DensityMatrix | None = None
    spin_density: DensityMatrix | None = None
    records: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
