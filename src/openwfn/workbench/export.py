"""Standalone offline HTML workbench exporter."""

from html import escape
from pathlib import Path

from ..model import CalculationData
from ..results import ResultRecord
from .payload import WorkbenchPayload


def export_workbench(
    data: CalculationData,
    path: Path,
    *,
    title: str = "openWFN Molecular Workbench",
    overwrite: bool = False,
) -> Path:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output exists: {path}. Pass overwrite=True to replace it.")
    asset_path = Path(__file__).resolve().parents[1] / "assets" / "3Dmol-min.js"
    if not asset_path.exists():
        raise FileNotFoundError(f"Missing bundled viewer asset: {asset_path}")
    engine = asset_path.read_text(encoding="utf-8").replace("</script>", "<\\/script>")
    payload = WorkbenchPayload.from_calculation(data, include_fields=True).to_json().replace("<", "\\u003c")
    document = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title><style>
:root{color-scheme:dark;--bg:#08111f;--panel:#101c2d;--line:#26364d;--text:#e7eef8;--muted:#9db0c9;--accent:#42c8f5}
*{box-sizing:border-box}body{margin:0;font:16px/1.45 system-ui,sans-serif;background:var(--bg);color:var(--text)}
.topbar{height:64px;display:flex;align-items:center;justify-content:space-between;padding:0 20px;border-bottom:1px solid var(--line);background:#0b1626}
.brand{font-weight:750;letter-spacing:.02em}.brand span{color:var(--accent)}.layout{display:grid;grid-template-columns:220px minmax(320px,1fr) 300px;height:calc(100vh - 96px)}
aside{background:var(--panel);padding:16px;border-right:1px solid var(--line)}#property-panel{border-right:0;border-left:1px solid var(--line);overflow:auto}
.workspace{display:block;width:100%;padding:11px 12px;margin:4px 0;text-align:left;color:var(--text);background:transparent;border:1px solid transparent;border-radius:7px;font:inherit;cursor:pointer}
.workspace:hover,.workspace.active{background:#172941;border-color:#315071}.workspace:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
#viewer{width:100%;height:100%;min-height:420px}.panel-title{font-size:.8rem;text-transform:uppercase;letter-spacing:.1em;color:var(--muted)}
.property{padding:10px 0;border-bottom:1px solid var(--line)}.property strong{display:block;color:var(--muted);font-size:.85rem}.status{height:32px;padding:6px 18px;border-top:1px solid var(--line);color:var(--muted);font-size:.85rem}
.measurement-controls[hidden]{display:none}.measure-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin:12px 0}.measure-button,#measurement-reset{padding:9px;border:1px solid var(--line);border-radius:6px;background:#14243a;color:var(--text);cursor:pointer}.measure-button.active{border-color:var(--accent);color:var(--accent)}.measure-button:focus-visible,#measurement-reset:focus-visible{outline:3px solid var(--accent);outline-offset:2px}.measurement-readout{min-height:2.8rem;padding:9px;margin:8px 0;background:#0b1626;border-radius:6px}
.surface-controls[hidden]{display:none}.surface-controls label{display:block;margin-top:12px;color:var(--muted)}#field-select,#isovalue{width:100%;margin-top:6px}#field-select{padding:8px;background:#14243a;color:var(--text);border:1px solid var(--line);border-radius:6px}.legend-row{display:flex;gap:12px;margin-top:10px}.swatch{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:5px}.positive{background:#2dd4bf}.negative{background:#f472b6}
@media(max-width:850px){.layout{grid-template-columns:170px 1fr}.layout>#property-panel{display:none}}@media(max-width:600px){.layout{display:block;height:auto}#workflow-sidebar{display:flex;overflow:auto;border-right:0}.workspace{min-width:max-content}#viewer{height:65vh}.topbar{height:auto;padding:14px}.status{height:auto}}
</style></head><body><header class="topbar"><div class="brand"><span>open</span>WFN Workbench</div><div>__TITLE__</div></header>
<main class="layout"><aside id="workflow-sidebar" aria-label="Scientific workspaces"><div class="panel-title">Workspaces</div>
<button class="workspace active" data-workspace="structure">Structure</button><button class="workspace" data-workspace="orbitals">Orbitals</button><button class="workspace" data-workspace="density">Density</button><button class="workspace" data-workspace="esp">ESP</button><button class="workspace" data-workspace="measurements">Measurements</button></aside>
<section id="viewer" aria-label="Three-dimensional molecule viewer"></section><aside id="property-panel"><div class="panel-title">Properties</div><div id="properties"></div>
<section id="measurement-controls" class="measurement-controls" hidden><div class="measure-grid" role="group" aria-label="Measurement type"><button class="measure-button active" data-measurement="distance">Distance</button><button class="measure-button" data-measurement="angle">Angle</button><button class="measure-button" data-measurement="dihedral">Dihedral</button><button id="measurement-reset">Reset</button></div><strong>Selected atoms</strong><div id="measurement-selection" class="measurement-readout">None</div><strong>Result</strong><div id="measurement-result" class="measurement-readout" aria-live="polite">Select two atoms</div></section>
<section id="surface-controls" class="surface-controls" hidden><label for="field-select">Scientific field</label><select id="field-select"></select><label for="isovalue">Isovalue: <output id="isovalue-output"></output></label><input id="isovalue" type="range" min="0.001" max="0.1" step="0.001"><div id="surface-legend" class="legend-row"><span><i class="swatch positive"></i>Positive</span><span><i class="swatch negative"></i>Negative</span></div><div id="surface-metadata" class="measurement-readout"></div></section></aside></main>
<footer id="status-line" class="status">Offline · molecular data remains on this device · Structure workspace</footer>
<script id="openwfn-workbench" type="application/json">__PAYLOAD__</script><script>__ENGINE__</script><script>
const payload=JSON.parse(document.getElementById('openwfn-workbench').textContent);
const atoms=payload.molecule.atoms;const xyz=[String(atoms.length),'openWFN workbench',...atoms.map(a=>`${a.symbol} ${a.coordinates.join(' ')}`)].join('\n');
const viewer=$3Dmol.createViewer('viewer',{backgroundColor:'#08111f'});viewer.addModel(xyz,'xyz');viewer.setStyle({}, {stick:{radius:.16},sphere:{scale:.28}});viewer.zoomTo();viewer.render();
const props=document.getElementById('properties');const measurementControls=document.getElementById('measurement-controls');const surfaceControls=document.getElementById('surface-controls');const fieldSelect=document.getElementById('field-select');const isovalue=document.getElementById('isovalue');let activeWorkspace='structure';let measurementMode='distance';let measurementSelection=[];let selectionLabels=[];
function vector(a,b){return [a[0]-b[0],a[1]-b[1],a[2]-b[2]]}function dot(a,b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]}function norm(a){return Math.sqrt(dot(a,a))}function cross(a,b){return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]}
function calculateDistance(a,b){return norm(vector(a,b))}function calculateAngle(a,b,c){const u=vector(a,b),v=vector(c,b);return Math.acos(Math.max(-1,Math.min(1,dot(u,v)/(norm(u)*norm(v)))))*180/Math.PI}function calculateDihedral(a,b,c,d){const b0=vector(a,b),b1=vector(c,b),b2=vector(d,c),n=norm(b1),axis=b1.map(x=>x/n),v=b0.map((x,i)=>x-axis[i]*dot(b0,axis)),w=b2.map((x,i)=>x-axis[i]*dot(b2,axis));return Math.atan2(dot(cross(axis,v),w),dot(v,w))*180/Math.PI}
function resetMeasurement(){measurementSelection=[];selectionLabels.forEach(label=>viewer.removeLabel(label));selectionLabels=[];document.getElementById('measurement-selection').textContent='None';document.getElementById('measurement-result').textContent=`Select ${{distance:2,angle:3,dihedral:4}[measurementMode]} atoms`;viewer.render()}
function selectMeasurementAtom(index){if(activeWorkspace!=='measurements')return;const required={distance:2,angle:3,dihedral:4}[measurementMode];if(measurementSelection.includes(index)||measurementSelection.length>=required)return;measurementSelection.push(index);const atom=atoms[index];selectionLabels.push(viewer.addLabel(String(index+1),{position:{x:atom.coordinates[0],y:atom.coordinates[1],z:atom.coordinates[2]},backgroundColor:'#147da1',fontColor:'white'}));document.getElementById('measurement-selection').textContent=measurementSelection.map(i=>`${i+1}:${atoms[i].symbol}`).join(' → ');if(measurementSelection.length===required){const p=measurementSelection.map(i=>atoms[i].coordinates);let value,unit;if(measurementMode==='distance'){value=calculateDistance(p[0],p[1]);unit='Å'}else if(measurementMode==='angle'){value=calculateAngle(p[0],p[1],p[2]);unit='°'}else{value=calculateDihedral(p[0],p[1],p[2],p[3]);unit='°'}document.getElementById('measurement-result').textContent=`${value.toFixed(6)} ${unit}`}viewer.render()}
viewer.setClickable({},true,atom=>selectMeasurementAtom(atom.index));document.querySelectorAll('.measure-button').forEach(button=>button.addEventListener('click',()=>{measurementMode=button.dataset.measurement;document.querySelectorAll('.measure-button').forEach(b=>b.classList.toggle('active',b===button));resetMeasurement()}));document.getElementById('measurement-reset').addEventListener('click',resetMeasurement);
function renderSurface(){viewer.removeAllSurfaces();const field=payload.fields.find(item=>item.id===fieldSelect.value);if(!field){viewer.render();return}const level=Number(isovalue.value);document.getElementById('isovalue-output').textContent=level.toFixed(3);const volume=new $3Dmol.VolumeData(field.cube,'cube');viewer.addIsosurface(volume,{isoval:level,color:'#2dd4bf',opacity:.72});if(field.signed)viewer.addIsosurface(volume,{isoval:-level,color:'#f472b6',opacity:.72});document.getElementById('surface-legend').hidden=!field.signed;document.getElementById('surface-metadata').textContent=`${field.units} · spacing ${field.grid.spacing_bohr} bohr · ${field.validation_status}`;viewer.render()}
function configureSurfaces(workspace){const fields=payload.fields.filter(field=>field.workspace===workspace);surfaceControls.hidden=fields.length===0;fieldSelect.replaceChildren(...fields.map(field=>{const option=document.createElement('option');option.value=field.id;option.textContent=field.name;return option}));if(fields.length){isovalue.value=String(fields[0].isovalue);renderSurface()}else{viewer.removeAllSurfaces();viewer.render()}}
fieldSelect.addEventListener('change',()=>{const field=payload.fields.find(item=>item.id===fieldSelect.value);if(field)isovalue.value=String(field.isovalue);renderSurface()});isovalue.addEventListener('input',renderSurface);
function showWorkspace(name){activeWorkspace=name;document.querySelectorAll('.workspace').forEach(b=>b.classList.toggle('active',b.dataset.workspace===name));measurementControls.hidden=name!=='measurements';props.hidden=name==='measurements'||['orbitals','density','esp'].includes(name);configureSurfaces(name);
const source=name==='structure'?{...payload.molecule,...payload.properties.calculation}:payload.properties[name]||{status:'No embedded field'};props.replaceChildren();Object.entries(source).forEach(([key,value])=>{const row=document.createElement('div');row.className='property';const label=document.createElement('strong');label.textContent=key.replaceAll('_',' ');row.append(label,document.createTextNode(typeof value==='object'?JSON.stringify(value):String(value)));props.append(row)});if(name==='measurements')resetMeasurement();document.getElementById('status-line').textContent=`Offline · molecular data remains on this device · ${name[0].toUpperCase()+name.slice(1)} workspace`}
document.querySelectorAll('.workspace').forEach(button=>button.addEventListener('click',()=>showWorkspace(button.dataset.workspace)));showWorkspace('structure');
</script></body></html>"""
    document = document.replace("__TITLE__", escape(title)).replace("__PAYLOAD__", payload).replace("__ENGINE__", engine)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")
    return path


def export_workbench_record(
    data: CalculationData,
    path: Path,
    *,
    overwrite: bool = False,
) -> ResultRecord:
    exported = export_workbench(data, path, overwrite=overwrite)
    return ResultRecord(
        kind="molecular_workbench",
        data={
            "output": str(exported),
            "offline": True,
            "schema_version": "1.0",
        },
        validation_status="Stable",
    )
