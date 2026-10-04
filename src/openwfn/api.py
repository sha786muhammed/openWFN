"""Stable Python interface to openWFN calculations."""

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from .analysis.hirshfeld import HirshfeldSettings
from .analysis.registry import run_analysis, run_analysis_safe
from .analysis.structure_summary import center_counts
from .capabilities import Capability, infer_capabilities
from .data import INTEROP_SCHEMA_VERSION, OpenWFNData, StructureData
from .errors import DataUnavailableError
from .ingest import load_input
from .model import MODEL_SCHEMA_VERSION, Molecule
from .results import ResultRecord
from .services import (
    density_integration,
    electrostatic_potential_point,
    geometry_angle,
    geometry_dihedral,
    geometry_distance,
)


@dataclass(frozen=True, slots=True)
class OpenWFNCalculation:
    data: OpenWFNData

    @property
    def molecule(self) -> Molecule:
        if self.data.calculation is None:
            raise DataUnavailableError("This input does not contain a complete isolated molecular calculation.")
        return self.data.calculation.molecule

    def capabilities(self) -> dict[str, Capability]:
        """Return capabilities inferred from normalized data actually present."""

        return infer_capabilities(self.data)

    def _provenance_payload(self) -> dict[str, object]:
        source = self.data.provenance
        return {
            "input_sha256": source.sha256 if source else None,
            "interop_schema_version": INTEROP_SCHEMA_VERSION,
            "model_schema_version": MODEL_SCHEMA_VERSION,
            "parser": source.parser if source else None,
            "parser_version": source.parser_version if source else None,
            "backend": getattr(source, "backend", None) if source else None,
            "backend_version": getattr(source, "backend_version", None) if source else None,
            "source_format": source.source_format if source else None,
            "source_path": source.source_path if source else None,
            "source_program": self.data.metadata.source_program,
            "source_program_version": self.data.metadata.source_program_version,
            "transformations": list(source.transformations) if source else [],
        }

    def _with_provenance(self, result: ResultRecord) -> ResultRecord:
        source = self.data.provenance
        source_warnings = source.warnings if source else ()
        return replace(
            result,
            provenance=self._provenance_payload(),
            warnings=tuple(dict.fromkeys((*result.warnings, *source_warnings))),
        )

    def _unavailable(self, kind: str, analysis_name: str, message: str) -> ResultRecord:
        return self._with_provenance(
            ResultRecord.failure(
                kind=kind,
                analysis_name=analysis_name,
                analysis_version="1",
                exception=DataUnavailableError(message),
                elapsed_seconds=0.0,
            )
        )

    def analyze_geometry(self) -> ResultRecord:
        """Return basic geometry metadata in the standard result envelope."""

        if self.data.calculation is not None:
            structure = self.data.calculation.molecule
            atom_count = len(structure.atoms)
            charge = structure.charge
            multiplicity = structure.multiplicity
        elif self.data.structure is not None:
            atom_count = len(self.data.structure.coordinates)
            charge = self.data.structure.charge
            multiplicity = self.data.structure.multiplicity
        else:
            return self._unavailable(
                "geometry_summary", "geometry_summary", "Atomic structure is not available for this input."
            )
        counts = center_counts(self.data.structure) if self.data.structure is not None else {}
        return self._with_provenance(
            ResultRecord(
                kind="geometry_summary",
                data={
                    "atom_count": atom_count,
                    "charge": charge,
                    "multiplicity": multiplicity,
                    **counts,
                },
            )
        )

    def analyze(self, name: str, **parameters) -> ResultRecord:
        """Run a named analysis through the shared versioned registry."""

        return run_analysis(self.data, name, **parameters)

    def _geometry_structure(self) -> Molecule | StructureData:
        if self.data.periodic is not None:
            raise DataUnavailableError("Periodic minimum-image geometry is not supported.")
        if self.data.structure is not None:
            return self.data.structure
        return self.molecule

    def geometry_distance(self, atom_i: int, atom_j: int) -> ResultRecord:
        return self._with_provenance(geometry_distance(self._geometry_structure(), atom_i, atom_j))

    def geometry_angle(self, atom_i: int, atom_j: int, atom_k: int) -> ResultRecord:
        return self._with_provenance(geometry_angle(self._geometry_structure(), atom_i, atom_j, atom_k))

    def geometry_dihedral(self, atom_i: int, atom_j: int, atom_k: int, atom_l: int) -> ResultRecord:
        return self._with_provenance(
            geometry_dihedral(self._geometry_structure(), atom_i, atom_j, atom_k, atom_l)
        )

    def orbitals(self, spin: Literal["alpha", "beta", "all"] = "alpha") -> ResultRecord:
        """Return frontier molecular-orbital energies for one or both spin channels."""

        if spin not in {"alpha", "beta", "all"}:
            raise ValueError("spin must be 'alpha', 'beta', or 'all'")
        analysis = {"alpha": "frontier", "beta": "beta-frontier", "all": "frontier-all"}[spin]
        return run_analysis_safe(self.data, analysis)

    def density(
        self,
        kind: Literal["total", "alpha", "beta", "spin"] = "total",
        *,
        spacing_bohr: float = 0.15,
        padding_bohr: float = 6.0,
    ) -> ResultRecord:
        """Integrate an electron-density component on a molecular grid."""

        if kind not in {"total", "alpha", "beta", "spin"}:
            raise ValueError("density kind must be 'total', 'alpha', 'beta', or 'spin'")
        if self.data.calculation is None:
            return self._unavailable(
                "density_integration",
                f"density-{kind}",
                "Density analysis requires a complete molecular wavefunction.",
            )
        try:
            return self._with_provenance(
                density_integration(self.data.calculation, kind, spacing_bohr, padding_bohr)
            )
        except DataUnavailableError as exc:
            return self._unavailable("density_integration", f"density-{kind}", str(exc))

    def esp(self, coordinates_angstrom: tuple[float, float, float], *,
            component: str = "total", method: str = "integrals",
            spacing_bohr: float = .15, padding_bohr: float = 6.) -> ResultRecord:
        """Point electrostatic potential in hartree/e; coordinates are angstrom."""
        if self.data.calculation is None:
            return self._unavailable("electrostatic_potential", "esp-point", "ESP requires a molecular wavefunction.")
        try:
            return self._with_provenance(electrostatic_potential_point(
                self.data.calculation, coordinates_angstrom, component,
                spacing_bohr, padding_bohr, method=method))
        except (DataUnavailableError, ValueError) as exc:
            return self._with_provenance(ResultRecord.failure(
                kind="electrostatic_potential", analysis_name="esp-point",
                analysis_version="1", exception=exc, elapsed_seconds=0.0))

    def pdos(self, *, group_by: str = "atom", method: str = "lowdin", sigma_ev: float = .3,
             spin: str = "all", energy_min_ev: float | None = None,
             energy_max_ev: float | None = None, points: int | None = None) -> ResultRecord:
        """Orbital-energy PDOS with explicitly named normalized AO projections."""
        return run_analysis_safe(self.data, "pdos", group_by=group_by, method=method,
            sigma_ev=sigma_ev, spin=spin, energy_min_ev=energy_min_ev,
            energy_max_ev=energy_max_ev, points=points)

    def dos(self, *, sigma_ev: float = .3, spin: str = "all",
            energy_min_ev: float | None = None, energy_max_ev: float | None = None,
            points: int | None = None) -> ResultRecord:
        """Gaussian orbital-energy DOS (width is sigma in eV)."""
        return run_analysis_safe(self.data, "dos", sigma_ev=sigma_ev, spin=spin,
            energy_min_ev=energy_min_ev, energy_max_ev=energy_max_ev, points=points)

    def mayer(self, *, threshold: float = .05) -> ResultRecord:
        """Return Mayer bond orders including the spin-density term."""
        return run_analysis_safe(self.data, "mayer", threshold=threshold)

    def orbital_composition(self, *, mo: int | str = "homo", spin: str = "alpha",
                            method: str = "lowdin") -> ResultRecord:
        """Return explicitly named AO/atom/shell MO projection fractions."""
        return run_analysis_safe(self.data, "orbital-composition", mo=mo, spin=spin, method=method)

    def orbital_cube(self, output: str | Path, *, mo: int | str = "homo",
                     spin: str = "alpha", spacing_bohr: float = 0.15,
                     padding_bohr: float = 6.0, overwrite: bool = False) -> ResultRecord:
        """Export signed MO amplitudes; public orbital numbers are one-based."""
        from .orbital_services import orbital_cube_export

        if self.data.calculation is None:
            return self._unavailable("orbital_cube", "orbital_cube", "MO cube requires a molecular wavefunction.")
        try:
            return self._with_provenance(orbital_cube_export(
                self.data.calculation, mo, spin, spacing_bohr, padding_bohr,
                Path(output), overwrite))
        except DataUnavailableError as exc:
            return self._unavailable("orbital_cube", "orbital_cube", str(exc))

    def hirshfeld(
        self,
        *,
        settings: HirshfeldSettings | None = None,
    ) -> ResultRecord:
        """Return native Hirshfeld populations with optional expert numerical settings."""

        return run_analysis_safe(self.data, "hirshfeld", settings=settings)

    def population(
        self,
        method: Literal["mulliken", "lowdin", "hirshfeld"] = "mulliken",
    ) -> ResultRecord:
        """Return Mulliken, symmetric Löwdin, or native Hirshfeld populations."""

        if method not in {"mulliken", "lowdin", "hirshfeld"}:
            raise ValueError("population method must be 'mulliken', 'lowdin', or 'hirshfeld'")
        return run_analysis_safe(self.data, method)


def load(path: str | Path, *, format_hint: str | None = None) -> OpenWFNCalculation:
    """Load any successfully normalized native or interoperability input."""

    return OpenWFNCalculation(load_input(Path(path), format_hint=format_hint))
