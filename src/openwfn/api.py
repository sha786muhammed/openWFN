"""Stable Python interface to openWFN calculations."""

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from .analysis.registry import run_analysis
from .errors import DataUnavailableError
from .model import (
    MODEL_SCHEMA_VERSION,
    CalculationData,
    CalculationMetadata,
    Molecule,
    VolumetricGrid,
)
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

    def _with_provenance(self, result: ResultRecord) -> ResultRecord:
        source = self.molecule.provenance
        provenance = {
            "input_sha256": source.sha256 if source else None,
            "model_schema_version": MODEL_SCHEMA_VERSION,
            "parser": source.parser if source else None,
            "parser_version": source.parser_version if source else None,
            "source_format": source.source_format if source else None,
            "source_path": source.source_path if source else None,
            "source_program": self.molecule.metadata.source_program,
            "source_program_version": self.molecule.metadata.source_program_version,
            "transformations": list(source.transformations) if source else [],
        }
        return replace(
            result,
            provenance=provenance,
            warnings=source.warnings if source else (),
        )

    def analyze_geometry(self) -> ResultRecord:
        """Return basic molecular geometry metadata in the standard result envelope."""

        return self._with_provenance(
            ResultRecord(
                kind="geometry_summary",
                data={
                    "atom_count": len(self.molecule.atoms),
                    "charge": self.molecule.charge,
                    "multiplicity": self.molecule.multiplicity,
                },
            )
        )

    def analyze(self, name: str) -> ResultRecord:
        """Run a named analysis through the shared versioned registry."""

        return run_analysis(self.data, name)

    def geometry_distance(self, atom_i: int, atom_j: int) -> ResultRecord:
        return self._with_provenance(geometry_distance(self.molecule, atom_i, atom_j))

    def geometry_angle(self, atom_i: int, atom_j: int, atom_k: int) -> ResultRecord:
        return self._with_provenance(geometry_angle(self.molecule, atom_i, atom_j, atom_k))

    def geometry_dihedral(self, atom_i: int, atom_j: int, atom_k: int, atom_l: int) -> ResultRecord:
        return self._with_provenance(
            geometry_dihedral(self.molecule, atom_i, atom_j, atom_k, atom_l)
        )

    def orbitals(self, spin: Literal["alpha", "beta", "all"] = "alpha") -> ResultRecord:
        """Return frontier molecular-orbital energies for one or both spin channels."""
        return self._with_provenance(orbital_frontier(self.data, spin))

    def density(
        self,
        kind: Literal["total", "alpha", "beta", "spin"] = "total",
        *,
        spacing_bohr: float = 0.15,
        padding_bohr: float = 6.0,
    ) -> ResultRecord:
        """Integrate an electron-density component on a molecular grid."""
        return self._with_provenance(
            density_integration(self.data, kind, spacing_bohr, padding_bohr)
        )

    def population(
        self,
        method: Literal["mulliken", "lowdin"] = "mulliken",
    ) -> ResultRecord:
        """Return Mulliken or symmetric Löwdin atomic populations."""
        return self._with_provenance(population_analysis(self.data, method))


def load(path: str | Path) -> OpenWFNCalculation:
    parsed = parse_input(Path(path))
    if isinstance(parsed, CalculationMetadata):
        raise DataUnavailableError(
            f"{path} contains calculation metadata rather than a molecular calculation."
        )
    if isinstance(parsed, VolumetricGrid):
        raise DataUnavailableError(
            f"{path} contains a volumetric grid rather than a molecular calculation."
        )
    if not isinstance(parsed, CalculationData):
        raise DataUnavailableError(f"{path} does not contain a supported molecular calculation.")
    return OpenWFNCalculation(parsed)
