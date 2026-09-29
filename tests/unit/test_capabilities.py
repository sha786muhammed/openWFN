from dataclasses import replace
from pathlib import Path

from openwfn.data import (
    IntegralData,
    OpenWFNData,
    PeriodicData,
    SourceMetadata,
    StructureData,
    wrap_calculation,
)
from openwfn.model import Provenance, VolumetricGrid
from openwfn.parsers.gaussian.fchk import parse_fchk

ROOT = Path(__file__).resolve().parents[2]


def _provenance(source_format: str) -> Provenance:
    return Provenance(
        source_path="fixture",
        sha256="1" * 64,
        parser="test",
        source_format=source_format,
    )


def _container(
    *,
    structure: StructureData | None = None,
    periodic: PeriodicData | None = None,
    grids: tuple[VolumetricGrid, ...] = (),
    integrals: IntegralData | None = None,
    source_format: str = "test",
) -> OpenWFNData:
    return OpenWFNData(
        calculation=None,
        structure=structure,
        periodic=periodic,
        grids=grids,
        integrals=integrals,
        metadata=SourceMetadata(),
        provenance=_provenance(source_format),
    )


def test_wrapped_fchk_exposes_wavefunction_capabilities() -> None:
    from openwfn.capabilities import infer_capabilities

    calculation = parse_fchk(ROOT / "examples" / "water" / "water.fchk")
    capabilities = infer_capabilities(wrap_calculation(calculation))

    assert capabilities["structure"].state == "available"
    assert capabilities["molecular_metadata"].state == "available"
    assert capabilities["isolated_molecule"].state == "available"
    assert capabilities["basis"].state == "available"
    assert capabilities["alpha_orbitals"].state == "available"
    assert capabilities["orbital_occupations"].state == "available"
    assert capabilities["total_density"].state == "available"
    assert capabilities["ao_overlap"].state == "derived"
    assert capabilities["electronic_energy"].state == "available"


def test_structure_only_has_no_wavefunction_capabilities() -> None:
    from openwfn.capabilities import infer_capabilities

    data = _container(
        structure=StructureData(coordinates=((0.0, 0.0, 0.0),), atomic_numbers=(1,)),
        source_format="xyz",
    )
    capabilities = infer_capabilities(data)

    assert capabilities["structure"].state == "available"
    assert capabilities["basis"].state == "missing"
    assert capabilities["alpha_orbitals"].state == "missing"
    assert capabilities["total_density"].state == "missing"


def test_periodic_grid_and_integral_inputs_expose_only_real_capabilities() -> None:
    from openwfn.capabilities import infer_capabilities

    periodic = _container(
        structure=StructureData(coordinates=((0.0, 0.0, 0.0),), atomic_numbers=(14,)),
        periodic=PeriodicData(
            cell_vectors=((5.0, 0.0, 0.0), (0.0, 5.0, 0.0), (0.0, 0.0, 5.0))
        ),
        source_format="poscar",
    )
    grid = VolumetricGrid(
        origin=(0.0, 0.0, 0.0),
        axes=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        shape=(1, 1, 1),
        values=(0.5,),
        value_unit="field",
    )
    grid_only = _container(grids=(grid,), source_format="cube")
    integral_only = _container(
        integrals=IntegralData(n_orbitals=2, n_electrons=2), source_format="fcidump"
    )

    periodic_caps = infer_capabilities(periodic)
    assert periodic_caps["periodic_cell"].state == "available"
    assert periodic_caps["isolated_molecule"].state == "missing"

    grid_caps = infer_capabilities(grid_only)
    assert grid_caps["volumetric_grid"].state == "available"
    assert grid_caps["alpha_orbitals"].state == "missing"

    integral_caps = infer_capabilities(integral_only)
    assert integral_caps["integrals"].state == "available"
    assert integral_caps["alpha_orbitals"].state == "missing"


def test_capabilities_do_not_change_when_only_source_format_changes() -> None:
    from openwfn.capabilities import infer_capabilities

    structure = StructureData(coordinates=((0.0, 0.0, 0.0),), atomic_numbers=(1,))
    first = _container(structure=structure, source_format="xyz")
    second = replace(first, provenance=_provenance("molden"))

    assert infer_capabilities(first) == infer_capabilities(second)


def test_requirement_evaluation_accepts_available_or_derived_alternatives() -> None:
    from openwfn.capabilities import CapabilityRequirement, evaluate_requirements

    calculation = parse_fchk(ROOT / "examples" / "water" / "water.fchk")
    availability = evaluate_requirements(
        wrap_calculation(calculation),
        (
            CapabilityRequirement("wavefunction", ("alpha_orbitals", "beta_orbitals")),
            CapabilityRequirement("overlap", ("ao_overlap",)),
        ),
    )

    assert availability.available is True
    assert availability.missing_requirements == ()


def test_periodic_structure_cannot_run_existing_isolated_summary() -> None:
    from openwfn.analysis.registry import run_analysis_safe

    data = _container(
        structure=StructureData(coordinates=((0.0, 0.0, 0.0),), atomic_numbers=(14,)),
        periodic=PeriodicData(
            cell_vectors=((5.0, 0.0, 0.0), (0.0, 5.0, 0.0), (0.0, 0.0, 5.0))
        ),
        source_format="poscar",
    )

    result = run_analysis_safe(data, "summary")

    assert result.status == "failed"
    assert result.validation_status == "Unsupported"
    assert result.error is not None
    assert result.error.category == "DataUnavailableError"
    assert "isolated molecule" in result.error.message.lower()


def test_grid_only_frontier_is_structured_unsupported_result() -> None:
    from openwfn.analysis.registry import run_analysis_safe

    grid = VolumetricGrid(
        origin=(0.0, 0.0, 0.0),
        axes=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        shape=(1, 1, 1),
        values=(0.5,),
        value_unit="field",
    )
    result = run_analysis_safe(_container(grids=(grid,), source_format="cube"), "frontier")

    assert result.status == "failed"
    assert result.validation_status == "Unsupported"
    assert result.error is not None
    assert "alpha orbitals" in result.error.message.lower()
