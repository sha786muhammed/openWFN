import json
from dataclasses import replace
from pathlib import Path

import pytest

from openwfn import load
from openwfn.analysis.structure_summary import structure_summary
from openwfn.app import CommandContext
from openwfn.data import OpenWFNData, SourceMetadata, StructureData
from openwfn.parsers.gaussian.fchk import parse_fchk
from openwfn.presentation import render
from openwfn.results import ResultRecord
from openwfn.services import electrostatic_potential_point

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / "examples/water/water.fchk"


def test_xyz_summary_uses_elements_without_inventing_electronic_data(tmp_path):
    path = tmp_path / "water.xyz"
    path.write_text("3\nwater\nO 0 0 0\nH 0 0 1\nH 1 0 0\n")
    result = load(path).analyze("summary")
    assert result.data["formula"] == "H2O"
    assert result.data["atoms"] == 3
    assert result.data["electron_count"] is None
    assert result.data["unknown_effective_charges"] == 3
    assert result.data["physical_nuclei"] is None
    assert result.status == "partial"


def test_summary_excludes_explicit_ghost_and_preserves_ecp_element():
    data = OpenWFNData(
        calculation=None,
        structure=StructureData(
            coordinates=((0., 0., 0.), (1., 0., 0.), (2., 0., 0.)),
            atomic_numbers=(8, 1, 1), effective_nuclear_charges=(6., 0., None),
        ), periodic=None, grids=(), integrals=None, metadata=SourceMetadata(), provenance=None,
    )
    result = structure_summary(data)
    assert result.data["formula"] == "HO"
    assert result.data["atoms"] == 2
    assert result.data["unknown_effective_charges"] == 1


def test_status_separates_validation_from_source_job():
    result = load(WATER).analyze("summary")
    text = render(result, CommandContext(format="plain", input_path=WATER))
    assert "Analysis Validation Status: Stable" in text
    assert "Result Status: success" in text
    assert "Source Calculation Status: Unknown from FCHK" in text


@pytest.mark.parametrize("termination,label", [(True, "Normal"), (False, "Not normal"), (None, "Unknown")])
def test_output_termination_is_distinct_from_result_status(termination, label):
    result = ResultRecord(kind="output_properties", data={"normal_termination": termination}, status="partial")
    text = render(result, CommandContext(format="plain"))
    assert f"Source Job Termination: {label}" in text
    assert "Result Status: partial" in text


@pytest.mark.parametrize("component", ["nuclear", "total", "mulliken", "lowdin"])
def test_esp_at_nucleus_has_specific_catchable_error(component):
    water = parse_fchk(WATER)
    with pytest.raises(ValueError, match="singular.*nuclear|nuclear.*singular"):
        electrostatic_potential_point(water, water.molecule.atoms[0].coordinates, component, .5, 2.)


def test_compact_properties_preserves_diagnostics_and_full_json():
    coordinates = [[float(i), 0., 0.] for i in range(100)]
    charges = [0.] * 100
    result = ResultRecord(kind="output_properties", data={
        "coordinates_angstrom": coordinates,
        "reported_atomic_charges": {"mulliken": {"values": charges, "charge_sum_residual": .001}},
    }, warnings=("Charge sum exceeds tolerance",))
    text = render(result, CommandContext(format="plain"))
    assert "100 entries" in text
    assert str(coordinates) not in text
    assert "charge_sum_residual" in text and "0.001" in text
    assert "Charge sum exceeds tolerance" in text
    assert "--verbose" in text
    verbose = render(result, CommandContext(format="plain", verbose=True))
    assert str(coordinates) in verbose
    assert json.loads(render(result, CommandContext(format="json")))["data"]["coordinates_angstrom"] == coordinates


def test_nuclear_esp_at_zero_charge_ghost_is_not_singular():
    water = parse_fchk(WATER)
    atoms = list(water.molecule.atoms)
    atoms[0] = replace(atoms[0], nuclear_charge=0.)
    data = replace(water, molecule=replace(water.molecule, atoms=tuple(atoms)))
    result = electrostatic_potential_point(data, atoms[0].coordinates, "nuclear", .5, 2.)
    assert result.status == "success"
