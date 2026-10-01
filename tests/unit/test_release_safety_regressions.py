import json
import re
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from openwfn import load
from openwfn.analysis.grids import molecular_grid_points
from openwfn.api import OpenWFNCalculation
from openwfn.batch import discover_inputs
from openwfn.data import OpenWFNData, SourceMetadata, StructureData
from openwfn.exporters.structures import write_structure
from openwfn.parsers.gaussian.fchk import parse_fchk
from openwfn.reporting import build_report, build_report_record
from openwfn.services import electrostatic_potential_point
from openwfn.workbench.export import export_workbench
from openwfn.workbench.payload import WorkbenchPayload

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def water():
    return parse_fchk(ROOT / "examples/water/water.fchk")


@pytest.fixture
def bad_density(water):
    return replace(water, total_density=replace(
        water.total_density,
        values=tuple(tuple(1.1 * v for v in row) for row in water.total_density.values),
    ))


def test_fine_grid_rejected_before_mesh_allocation(water):
    with patch("openwfn.analysis.grids.np.meshgrid", side_effect=AssertionError("unsafe allocation")):
        with pytest.raises(ValueError, match="limit"):
            molecular_grid_points(water.molecule, spacing_bohr=0.02, padding_bohr=6.)


def test_cli_density_resource_failure_is_json():
    result = subprocess.run([
        sys.executable, "-m", "openwfn.cli", "--format", "json",
        str(ROOT / "examples/water/water.fchk"), "density", "integrate", "--spacing", "0.02",
    ], capture_output=True, text=True, timeout=15)
    assert result.returncode != 0
    record = json.loads(result.stdout)
    assert record["status"] == "failed"
    assert "limit" in record["error"]["message"]


def test_python_density_resource_failure_is_catchable():
    calc = load(ROOT / "examples/water/water.fchk")
    with pytest.raises(ValueError, match="limit"):
        calc.density(spacing_bohr=0.02)


def test_batch_discovers_molden_compound_extension(tmp_path):
    path = tmp_path / "water.molden.input"
    path.write_bytes((ROOT / "tests/fixtures/interop/molden/water.molden").read_bytes())
    result = discover_inputs([tmp_path])
    assert path in result.inputs


@pytest.mark.parametrize("spacing", [float("nan"), float("inf")])
def test_nonfinite_grid_spacing_rejected(water, spacing):
    with pytest.raises(ValueError, match="finite"):
        molecular_grid_points(water.molecule, spacing_bohr=spacing, padding_bohr=6.)


@pytest.mark.parametrize("name", ["water.molden.input", "water.unknown"])
def test_molden_compound_extension_and_header(tmp_path, name):
    pytest.importorskip("iodata")
    path = tmp_path / name
    path.write_bytes((ROOT / "tests/fixtures/interop/molden/water.molden").read_bytes())
    assert load(path).analyze("summary").data["formula"] == "H2O"


@pytest.mark.parametrize("method", ["mulliken", "lowdin"])
def test_charge_esp_preserves_conservation_failure(bad_density, method):
    result = electrostatic_potential_point(bad_density, (4., 4., 4.), method, .5, 2.)
    assert result.status == "partial"
    assert any("conservation" in w.lower() for w in result.warnings)


def test_workbench_preserves_population_failure(bad_density):
    result = WorkbenchPayload.from_calculation(bad_density).properties["mulliken"]
    assert result["status"] == "partial"
    assert any("conservation" in w.lower() for w in result["warnings"])


def test_workbench_preserves_ghost_identity(water):
    atoms = (replace(water.molecule.atoms[0], nuclear_charge=0.), *water.molecule.atoms[1:])
    data = replace(water, molecule=replace(water.molecule, atoms=atoms))
    atom = WorkbenchPayload.from_calculation(data).molecule["atoms"][0]
    assert atom["is_ghost"] is True
    assert atom["nuclear_charge"] == 0.


def test_workbench_without_virtual_orbitals_keeps_homo(water):
    orbitals = replace(water.alpha_orbitals, occupations=tuple(2. for _ in water.alpha_orbitals.occupations))
    data = replace(water, alpha_orbitals=orbitals, total_density=None)
    result = WorkbenchPayload.from_calculation(data, include_fields=True)
    assert any(f["id"] == "orbital-homo" for f in result.fields)
    assert result.properties["frontier"]["status"] == "partial"


@pytest.mark.parametrize("fmt,suffix", [("markdown", "md"), ("html", "html")])
def test_report_displays_conservation_warning(bad_density, tmp_path, fmt, suffix):
    path = tmp_path / f"report.{suffix}"
    build_report(bad_density, ["mulliken"], path, fmt, "test", {})
    visible = path.read_text().split('<script id="openwfn-report"')[0]
    assert "Population charge conservation failed" in visible
    assert "partial" in visible.lower()


@pytest.mark.parametrize("fmt", ["xyz", "pdb", "mol", "sdf"])
def test_structure_export_warns_about_charge_and_spin_loss(water, tmp_path, fmt):
    molecule = replace(water.molecule, charge=1, multiplicity=2)
    warnings = write_structure(molecule, tmp_path / f"charged.{fmt}", fmt)
    assert any("molecular charge" in w.lower() for w in warnings)
    assert any("multiplicity" in w.lower() for w in warnings)


def test_geometry_requires_coordinates_not_wavefunction():
    structure = StructureData(((0., 0., 0.), (0., 0., 1.), (1., 0., 1.), (1., 1., 1.)), (1, 1, 1, 1))
    calc = OpenWFNCalculation(OpenWFNData(None, structure, None, (), None, SourceMetadata(), None))
    assert calc.geometry_distance(1, 2).data["value"] == 1.
    assert calc.geometry_angle(1, 2, 3).data["value"] == 90.
    assert abs(calc.geometry_dihedral(1, 2, 3, 4).data["value"]) == 90.


def test_report_record_preserves_partial_status(bad_density, tmp_path):
    result = build_report_record(bad_density, ("mulliken",), tmp_path / "report.md", "markdown", "test")
    assert result.status == "partial"
    assert any("conservation" in w.lower() for w in result.warnings)


def test_workbench_marks_embedded_density_validation(bad_density):
    payload = WorkbenchPayload.from_calculation(bad_density, include_fields=True)
    density = next(f for f in payload.fields if f["id"] == "density-total")
    assert density["status"] == "partial"
    assert density["warnings"]


def test_workbench_visible_warning_and_ghost_hooks(water, tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for generated viewer behavior checks")
    path = tmp_path / "workbench.html"
    export_workbench(water, path)
    text = path.read_text()
    surface = re.search(r"^function renderSurface\(\).*?$", text, re.MULTILINE).group()
    ghosts = re.search(r"^function markGhostCenters\(\).*?$", text, re.MULTILINE).group()
    script = """
const nodes={};const document={getElementById:id=>nodes[id]||(nodes[id]={})};
const labels=[];const viewer={render(){},setStyle(){},addLabel(text){labels.push(text)},removeAllSurfaces(){},addIsosurface(){}};
const $3Dmol={VolumeData:class{}};
const atoms=[{is_ghost:true,coordinates:[0,0,0]},{is_ghost:false,coordinates:[0,0,1]}];
const payload={fields:[{id:'density',cube:'',units:'electron/bohr^3',grid:{spacing_bohr:.3},validation_status:'Experimental',status:'partial',warnings:['Conservation failed']} ]};
const fieldSelect={value:'density'},isovalue={value:'.02'};
""" + surface + "\n" + ghosts + """
renderSurface();markGhostCenters();
if(!nodes['surface-metadata'].textContent.includes('Conservation failed'))throw Error('warning hidden');
if(!nodes['surface-metadata'].textContent.includes('partial'))throw Error('status hidden');
if(JSON.stringify(labels)!==JSON.stringify(['Ghost 1']))throw Error('ghost not marked');
"""
    subprocess.run([node, "-e", script], capture_output=True, text=True, check=True)
