import json
import shutil
import subprocess
from pathlib import Path

import pytest

from openwfn.parsers.registry import load
from openwfn.workbench.export import export_workbench

ROOT = Path(__file__).resolve().parents[1]
WATER = ROOT / "examples" / "water" / "water.fchk"


def test_workbench_preserves_javascript_newline_escape(tmp_path: Path) -> None:
    output = tmp_path / "water-workbench.html"
    calculation = load(WATER)

    export_workbench(calculation, output)

    html = output.read_text(encoding="utf-8")
    assert ".join('\\n')" in html
    assert ".join('\n')" not in html


@pytest.fixture
def workbench_javascript(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is needed to execute the workbench interaction regression")
    output = export_workbench(load(WATER), tmp_path / "workbench.html")
    html = output.read_text(encoding="utf-8")
    functions = []
    for name in ("resetMeasurement", "selectMeasurementAtom", "clearFieldShapes",
                 "renderSurface", "configureSurfaces", "clearVibrationArrows"):
        functions.extend(line for line in html.splitlines() if line.startswith(f"function {name}("))
    start = html.index("function showWorkspace(")
    end = html.index("\ndocument.querySelectorAll('.workspace')", start)
    functions.append(html[start:end])
    # WebGL is not available in Node. Keep the bundled viewer's separate
    # shape/surface collections, including handle-specific removal semantics.
    setup = r"""
const elements = new Map();
function element(){return {value:'',hidden:false,textContent:'',append(){},
  replaceChildren(...children){this.value=children[0]?.value||''}}}
const document={getElementById(id){if(!elements.has(id))elements.set(id,element());return elements.get(id)},
  querySelectorAll(){return[]},createElement:element,createTextNode:value=>value};
const ghost={kind:'ghost'}, arrow={kind:'arrow'};
const viewer={shapes:[arrow],labels:[ghost],render(){},removeAllSurfaces(){},
  addIsosurface(volume,options){const shape={kind:'field',...options};this.shapes.push(shape);return shape},
  removeShape(shape){this.shapes=this.shapes.filter(item=>item!==shape)},
  addLabel(text,options){const label={text,...options};this.labels.push(label);return label},
  removeLabel(label){this.labels=this.labels.filter(item=>item!==label)}};
const $3Dmol={VolumeData:class {}};
const payload={molecule:{},properties:{calculation:{}},fields:[
  {id:'homo',workspace:'orbitals',name:'HOMO',signed:true,isovalue:.03,cube:'',grid:{spacing_bohr:.3}},
  {id:'density',workspace:'density',name:'Density',signed:false,isovalue:.02,cube:'',grid:{spacing_bohr:.3}}]};
const atoms=[{symbol:'O',coordinates:[0,0,0]},{symbol:'H',coordinates:[1,0,0]}];
let activeWorkspace='structure',measurementMode='distance',measurementSelection=[],selectionLabels=[],
  vibrationArrows=[arrow],fieldShapes=[];
const props=element(),measurementControls=element(),surfaceControls=element(),vibrationControls=element(),
  excitedStateControls=element(),fieldSelect=element(),isovalue=element();
function calculateDistance(){return 1}
"""

    def run(actions):
        script = setup + "\n".join(functions) + actions
        return json.loads(subprocess.check_output([node], input=script, text=True))

    return run


def test_changing_field_replaces_shapes_without_removing_other_overlays(workbench_javascript):
    state = workbench_javascript("""
configureSurfaces('orbitals');renderSurface();configureSurfaces('density');
console.log(JSON.stringify({fields:viewer.shapes.filter(s=>s.kind==='field').length,
  arrows:viewer.shapes.filter(s=>s.kind==='arrow').length,ghosts:viewer.labels.length}));
""")
    assert state == {"fields": 1, "arrows": 1, "ghosts": 1}


def test_structure_clears_fields_and_vibration_arrows(workbench_javascript):
    state = workbench_javascript("""
configureSurfaces('orbitals');showWorkspace('structure');
console.log(JSON.stringify({shapes:viewer.shapes.length,ghosts:viewer.labels.length}));
""")
    assert state == {"shapes": 0, "ghosts": 1}


def test_leaving_measurements_clears_selection_but_keeps_ghost_labels(workbench_javascript):
    state = workbench_javascript("""
showWorkspace('measurements');selectMeasurementAtom(0);selectMeasurementAtom(1);
showWorkspace('structure');
console.log(JSON.stringify({labels:viewer.labels.length,selected:measurementSelection,
  readout:document.getElementById('measurement-selection').textContent}));
""")
    assert state == {"labels": 1, "selected": [], "readout": "None"}
