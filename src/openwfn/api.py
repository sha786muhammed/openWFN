"""Stable Python interface to openWFN calculations."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import DataUnavailableError
from .model import CalculationData, Molecule
from .parsers.registry import load as parse_input
from .results import ResultRecord
from .services import (
    density_integration,
    geometry_angle,
    geometry_dihedral,
    geometry_distance,
    orbital_frontier,
    population_analysis,
)


@dataclass(frozen=True, slots=True)
class OpenWFNCalculation:
    data: CalculationData

    @property
    def molecule(self) -> Molecule:
        return self.data.molecule

    def analyze_geometry(self) -> dict[str, Any]:
        return {
            "atom_count": len(self.molecule.atoms),
            "charge": self.molecule.charge,
            "multiplicity": self.molecule.multiplicity,
        }

    def geometry_distance(self, atom_i: int, atom_j: int) -> ResultRecord:
        return geometry_distance(self.molecule, atom_i, atom_j)

    def geometry_angle(self, atom_i: int, atom_j: int, atom_k: int) -> ResultRecord:
        return geometry_angle(self.molecule, atom_i, atom_j, atom_k)

    def geometry_dihedral(
        self, atom_i: int, atom_j: int, atom_k: int, atom_l: int
    ) -> ResultRecord:
        return geometry_dihedral(self.molecule, atom_i, atom_j, atom_k, atom_l)

    def orbitals(self, spin: str = "alpha") -> ResultRecord:
        """Return frontier molecular-orbital energies for one spin channel."""
        return orbital_frontier(self.data, spin)

    def density(
        self,
        kind: str = "total",
        *,
        spacing_bohr: float = 0.15,
        padding_bohr: float = 6.0,
    ) -> ResultRecord:
        """Integrate an electron-density component on a molecular grid."""
        return density_integration(self.data, kind, spacing_bohr, padding_bohr)

    def population(self, method: str = "mulliken") -> ResultRecord:
        """Return Mulliken or symmetric Löwdin atomic populations."""
        return population_analysis(self.data, method)


def load(path: str | Path) -> OpenWFNCalculation:
    parsed = parse_input(Path(path))
    if not isinstance(parsed, CalculationData):
        raise DataUnavailableError(f"{path} contains a volumetric grid rather than a molecular calculation.")
    return OpenWFNCalculation(parsed)
