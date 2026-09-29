from pathlib import Path

from openwfn.analysis.registry import run_analysis, run_analysis_safe
from openwfn.capabilities import (
    CapabilityRequirement,
    evaluate_requirements,
    infer_capabilities,
)
from openwfn.data import OpenWFNData, PeriodicData, SourceMetadata, StructureData, wrap_calculation
from openwfn.model import VolumetricGrid
from openwfn.parsers.gaussian.fchk import parse_fchk

ROOT = Path(__file__).resolve().parents[2]
WATER_FCHK = ROOT / "examples" / "water" / "water.fchk"


def _wrapped_water() -> OpenWFNData:
    return wrap_calculation(parse_fchk(WATER_FCHK))


def _structure_only(*, periodic: bool = False) -> OpenWFNData:
    wrapped = _wrapped_water()
    return OpenWFNData(
        calculation=None,
        structure=wrapped.structure,
        periodic=(
            PeriodicData(
                cell_vectors=((10.0, 0.0, 0.0), (0.0, 10.0, 0.0), (0.0, 0.0, 10.0))
            )
            if periodic
            else None
        ),
        grids=(),
        integrals=None,
        metadata=SourceMetadata(source_program="fixture"),
        provenance=wrapped.provenance,
    )


def _grid_only() -> OpenWFNData:
    wrapped = _wrapped_water()
    grid = VolumetricGrid(
        origin=(0.0, 0.0, 0.0),
        axes=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        shape=(1, 1, 1),
        values=(0.5,),
        value_unit="electron/angstrom^3",
    )
    return OpenWFNData(
        calculation=None,
        structure=None,
        periodic=None,
        grids=(grid,),
        integrals=None,
        metadata=SourceMetadata(),
        provenance=wrapped.provenance,
    )


def test_wrapped_fchk_infers_direct_and_derived_capabilities() -> None:
    report = infer_capabilities(_wrapped_water())

    assert report["structure"].state == "available"
    assert report["molecular_metadata"].state == "available"
    assert report["basis"].state == "available"
    assert report["alpha_orbitals"].state == "available"
    assert report["total_density"].state == "available"
    assert report["ao_overlap"].state == "derived"
    assert report["isolated_system"].state == "available"


def test_structure_only_marks_wavefunction_capabilities_missing() -> None:
    report = infer_capabilities(_structure_only())

    assert report["structure"].state == "available"
    assert report["basis"].state == "missing"
    assert report["alpha_orbitals"].state == "missing"
    assert report["total_density"].state == "missing"
    assert report["volumetric_grid"].state == "missing"


def test_periodic_structure_fails_isolated_system_requirement() -> None:
    data = _structure_only(periodic=True)
    report = infer_capabilities(data)
    availability = evaluate_requirements(
        data,
        (CapabilityRequirement("isolated_system"), CapabilityRequirement("structure")),
    )

    assert report["periodic_cell"].state == "available"
    assert report["isolated_system"].state == "missing"
    assert availability.available is False
    assert availability.missing == ("isolated_system",)


def test_grid_only_supports_grid_but_not_frontier_requirements() -> None:
    data = _grid_only()
    report = infer_capabilities(data)
    availability = evaluate_requirements(
        data,
        (CapabilityRequirement("alpha_orbitals"),),
    )

    assert report["volumetric_grid"].state == "available"
    assert availability.available is False
    assert availability.missing == ("alpha_orbitals",)


def test_requirement_can_accept_any_one_of_multiple_capabilities() -> None:
    availability = evaluate_requirements(
        _wrapped_water(),
        (CapabilityRequirement("density_or_orbitals", any_of=("total_density", "alpha_orbitals")),),
    )

    assert availability.available is True
    assert availability.missing == ()


def test_registered_analysis_accepts_both_calculation_and_openwfn_data() -> None:
    calculation = parse_fchk(WATER_FCHK)
    wrapped = wrap_calculation(calculation)

    direct = run_analysis(calculation, "summary")
    normalized = run_analysis(wrapped, "summary")

    assert direct.data == normalized.data
    assert direct.status == "success"
    assert normalized.status == "success"


def test_unavailable_registered_analysis_returns_structured_unsupported_result() -> None:
    result = run_analysis_safe(_structure_only(), "frontier")

    assert result.status == "failed"
    assert result.validation_status == "Unsupported"
    assert result.error is not None
    assert result.error.category == "CapabilityUnavailableError"
    assert "alpha_orbitals" in result.error.message
