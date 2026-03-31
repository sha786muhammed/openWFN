# src/openwfn/export.py

import json
from pathlib import Path
import numpy as np  # type: ignore

from .constants import Z_TO_SYMBOL  # type: ignore


def export_vtk(filename: str, grid_points: np.ndarray, grid_shape: tuple[int, int, int], data: np.ndarray, data_name: str = "density") -> None:
    """
    Export 3D volumetric data to VTK format for ParaView/Mayavi.
    
    Args:
        filename: output .vtk file path.
        grid_points: (N, 3) matrix of coordinates.
        grid_shape: (nx, ny, nz) grid dimensions.
        data: (N,) flat array of values at each grid point.
        data_name: Name of the scalar field.
    """
    nx, ny, nz = grid_shape
    if nx <= 0 or ny <= 0 or nz <= 0:
        raise ValueError("grid_shape must have positive dimensions.")
    if grid_points.shape[0] != nx * ny * nz:
        raise ValueError("grid_points size does not match grid_shape.")
    if len(data) != nx * ny * nz:
        raise ValueError("data size does not match grid_shape.")
    
    with open(filename, 'w') as f:
        f.write("# vtk DataFile Version 3.0\n")
        f.write(f"openWFN {data_name} export\n")
        f.write("ASCII\n")
        f.write("DATASET STRUCTURED_POINTS\n")
        
        # Dimensions
        f.write(f"DIMENSIONS {nx} {ny} {nz}\n")
        
        # Origin (assume grid_points[0] is the min bound since we used meshgrid)
        origin = grid_points[0]
        f.write(f"ORIGIN {origin[0]} {origin[1]} {origin[2]}\n")
        
        # Infer spacing from neighboring points in flattened ijk-order grid.
        spacing_x = (grid_points[ny * nz][0] - grid_points[0][0]) if nx > 1 else 1.0
        spacing_y = (grid_points[nz][1] - grid_points[0][1]) if ny > 1 else 1.0
        spacing_z = (grid_points[1][2] - grid_points[0][2]) if nz > 1 else 1.0
        f.write(f"SPACING {spacing_x} {spacing_y} {spacing_z}\n")
        
        f.write(f"\nPOINT_DATA {len(data)}\n")
        f.write(f"SCALARS {data_name} float 1\n")
        f.write("LOOKUP_TABLE default\n")
        
        # Write data chunked
        for val in data:
            f.write(f"{val:.6e}\n")


def export_csv(filename: str, grid_points: np.ndarray, data: np.ndarray, data_name: str = "value") -> None:
    """Export points and values to a simple CSV."""
    with open(filename, 'w') as f:
        f.write(f"x,y,z,{data_name}\n")
        for (x, y, z), val in zip(grid_points, data):
            f.write(f"{x:.6f},{y:.6f},{z:.6f},{val:.6e}\n")


def export_json(filename: str, properties: dict[str, object]) -> None:
    """Dump scalar molecular properties into JSON."""
    with open(filename, 'w') as f:
        json.dump(properties, f, indent=4)


def export_molecule_viewer(
    filename: str | Path,
    atomic_numbers: list[int],
    coordinates: list[tuple[float, float, float]],
    title: str = "openWFN Molecule Viewer",
    show_labels: bool = True,
    style: str = "ballstick",
) -> None:
    """Export a standalone HTML molecule viewer using the vendored 3Dmol.js asset."""
    from .geometry import detect_bonds, molecular_formula  # type: ignore

    asset_path = Path(__file__).resolve().parent / "assets" / "3Dmol-min.js"
    if not asset_path.exists():
        raise FileNotFoundError(f"Missing bundled viewer asset: {asset_path}")

    viewer_js = asset_path.read_text(encoding="utf-8").replace("</script>", "<\\/script>")
    formula = molecular_formula(atomic_numbers)
    base_name = Path(filename).stem
    atom_records: list[dict[str, object]] = []
    for index, (z_number, (x, y, z_coord)) in enumerate(zip(atomic_numbers, coordinates), start=1):
        symbol = Z_TO_SYMBOL.get(z_number, "X")
        atom_records.append(
            {
                "serial": index,
                "elem": symbol,
                "x": x,
                "y": y,
                "z": z_coord,
                "label": f"{index}:{symbol}",
            }
        )
    bond_records = [
        {"i": i, "j": j, "order": 1}
        for i, j, _dist in detect_bonds(atomic_numbers, coordinates)
    ]

    xyz_lines = [str(len(atomic_numbers)), title]
    for z_number, (x, y, z_coord) in zip(atomic_numbers, coordinates):
        symbol = Z_TO_SYMBOL.get(z_number, "X")
        xyz_lines.append(f"{symbol} {x:.8f} {y:.8f} {z_coord:.8f}")

    xyz_json = json.dumps("\n".join(xyz_lines))
    atoms_json = json.dumps(atom_records)
    bonds_json = json.dumps(bond_records)
    file_base_json = json.dumps(base_name)
    initial_style = json.dumps(style)
    initial_labels = str(show_labels).lower()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #0f172a;
      --panel: #111827;
      --line: rgba(148, 163, 184, 0.18);
      --text: #e5e7eb;
      --muted: #94a3b8;
      --accent: #38bdf8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(56, 189, 248, 0.15), transparent 28%),
        linear-gradient(180deg, #111827, var(--bg));
    }}
    .shell {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 24px;
    }}
    .hero {{
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: end;
      flex-wrap: wrap;
      margin-bottom: 16px;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(1.7rem, 2.8vw, 2.35rem);
    }}
    .sub {{
      margin: 8px 0 0;
      color: var(--muted);
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 16px;
    }}
    .workspace {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 280px;
      gap: 18px;
      align-items: start;
    }}
    .chip {{
      padding: 8px 12px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.72);
      color: var(--muted);
      font-size: 0.92rem;
    }}
    .chip strong {{
      color: var(--text);
      margin-right: 6px;
    }}
    .viewer-panel, .side-panel {{
      border: 1px solid var(--line);
      border-radius: 20px;
      background: rgba(15, 23, 42, 0.72);
      box-shadow: 0 25px 60px rgba(0, 0, 0, 0.35);
    }}
    .viewer-panel {{
      padding: 14px;
      min-width: 0;
    }}
    .toolbar {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 12px;
    }}
    .toolbar-group {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      padding: 6px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: rgba(15, 23, 42, 0.78);
    }}
    .toolbar-label {{
      color: var(--muted);
      font-size: 0.85rem;
      padding: 8px 4px 8px 2px;
    }}
    .tool-btn {{
      appearance: none;
      border: 1px solid rgba(148, 163, 184, 0.18);
      background: rgba(30, 41, 59, 0.78);
      color: var(--text);
      border-radius: 10px;
      padding: 8px 12px;
      font-size: 0.92rem;
      cursor: pointer;
      transition: background-color 120ms ease, border-color 120ms ease, color 120ms ease;
    }}
    .tool-btn.active {{
      border-color: rgba(56, 189, 248, 0.5);
      background: rgba(14, 116, 144, 0.3);
      color: #bae6fd;
    }}
    .tool-btn:hover {{
      border-color: rgba(56, 189, 248, 0.36);
    }}
    #viewer {{
      position: relative;
      width: 100%;
      height: min(72vh, 720px);
      min-height: 520px;
      border: 1px solid var(--line);
      border-radius: 16px;
      overflow: hidden;
      background: var(--panel);
      isolation: isolate;
    }}
    .side-panel {{
      padding: 18px;
      display: grid;
      gap: 16px;
      min-width: 0;
    }}
    .panel-title {{
      margin: 0 0 10px;
      font-size: 1rem;
      letter-spacing: 0.02em;
    }}
    .kv {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      row-gap: 8px;
      font-size: 0.95rem;
    }}
    .kv span {{
      color: var(--muted);
    }}
    .kv strong {{
      color: var(--text);
    }}
    .mini-note {{
      color: var(--muted);
      font-size: 0.9rem;
      line-height: 1.45;
    }}
    .viewer-foot {{
      margin-top: 10px;
      color: var(--muted);
      font-size: 0.92rem;
    }}
    .note {{
      margin-top: 12px;
      color: var(--muted);
      font-size: 0.94rem;
    }}
    hr {{
      border: 0;
      border-top: 1px solid rgba(148, 163, 184, 0.12);
      margin: 0;
    }}
    code {{
      color: var(--accent);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    @media (max-width: 980px) {{
      .workspace {{
        grid-template-columns: 1fr;
      }}
      .side-panel {{
        order: 2;
      }}
    }}
    @media (max-width: 640px) {{
      .shell {{
        padding: 14px;
      }}
      #viewer {{
        height: min(62vh, 560px);
        min-height: 360px;
      }}
      .toolbar {{
        gap: 8px;
      }}
      .toolbar-group {{
        width: 100%;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <div class="hero">
      <div>
        <h1>{title}</h1>
        <p class="sub">Local 3Dmol.js viewer exported by openWFN</p>
      </div>
      <div class="chip"><strong>File</strong>{Path(filename).name}</div>
    </div>
    <div class="meta">
      <div class="chip"><strong>Atoms</strong>{len(atomic_numbers)}</div>
      <div class="chip"><strong>Formula</strong>{formula}</div>
      <div class="chip"><strong>Labels</strong>{"On" if show_labels else "Off"}</div>
      <div class="chip"><strong>Style</strong>{style}</div>
    </div>
    <div class="workspace">
      <div class="viewer-panel">
        <div class="toolbar">
          <div class="toolbar-group">
            <div class="toolbar-label">Style</div>
            <button class="tool-btn" data-style="ballstick">Ball & Stick</button>
            <button class="tool-btn" data-style="stick">Stick</button>
          </div>
          <div class="toolbar-group">
            <div class="toolbar-label">Labels</div>
            <button id="labels-toggle" class="tool-btn">Toggle</button>
          </div>
          <div class="toolbar-group">
            <div class="toolbar-label">View</div>
            <button id="reset-view" class="tool-btn">Reset</button>
          </div>
          <div class="toolbar-group">
            <div class="toolbar-label">Download</div>
            <button class="tool-btn" data-download="xyz">XYZ</button>
            <button class="tool-btn" data-download="pdb">PDB</button>
            <button class="tool-btn" data-download="sdf">SDF</button>
            <button class="tool-btn" data-download="png">PNG</button>
            <button class="tool-btn" data-download="jpeg">JPEG</button>
            <button class="tool-btn" data-download="svg">SVG</button>
          </div>
        </div>
        <div id="viewer"></div>
        <div class="viewer-foot">Rotate with drag, zoom with scroll, and right-drag to translate.</div>
      </div>
      <aside class="side-panel">
        <div>
          <h2 class="panel-title">Structure</h2>
          <div class="kv">
            <span>Formula</span><strong>{formula}</strong>
            <span>Atoms</span><strong>{len(atomic_numbers)}</strong>
            <span>Default style</span><strong>{style}</strong>
            <span>Labels</span><strong>{"On" if show_labels else "Off"}</strong>
          </div>
        </div>
        <hr>
        <div>
          <h2 class="panel-title">Usage</h2>
          <div class="mini-note">
            This viewer is fully local: the 3D engine is bundled into the exported HTML, so it does not rely on a CDN.
          </div>
        </div>
        <hr>
        <div>
          <h2 class="panel-title">Labels</h2>
          <div class="mini-note">
            Atom labels use <code>index:symbol</code>, for example <code>1:O</code> and <code>2:H</code>.
          </div>
        </div>
      </aside>
    </div>
    <div class="note">Local 3Dmol.js viewer exported by openWFN.</div>
  </div>
  <script>
{viewer_js}
  </script>
  <script>
    const atoms = {atoms_json};
    const bonds = {bonds_json};
    const xyzData = {xyz_json};
    const fileBase = {file_base_json};
    const viewer = $3Dmol.createViewer("viewer", {{ backgroundColor: "#111827" }});
    const labelsToggle = document.getElementById("labels-toggle");
    const resetViewButton = document.getElementById("reset-view");
    const styleButtons = Array.from(document.querySelectorAll("[data-style]"));
    const downloadButtons = Array.from(document.querySelectorAll("[data-download]"));
    let labelsVisible = {initial_labels};
    let currentStyle = {initial_style};
    let labelHandles = [];

    function styleConfig(name) {{
      if (name === "stick") {{
        return {{ stick: {{ radius: 0.22, colorscheme: "Jmol" }} }};
      }}
      return {{
        stick: {{ radius: 0.18, colorscheme: "Jmol" }},
        sphere: {{ scale: 0.32, colorscheme: "Jmol" }}
      }};
    }}

    function syncButtons() {{
      styleButtons.forEach((button) => {{
        button.classList.toggle("active", button.dataset.style === currentStyle);
      }});
      labelsToggle.classList.toggle("active", labelsVisible);
    }}

    function clearLabels() {{
      for (const handle of labelHandles) {{
        viewer.removeLabel(handle);
      }}
      labelHandles = [];
    }}

    function syncLabels() {{
      clearLabels();
      if (!labelsVisible) {{
        viewer.render();
        return;
      }}
      for (const atom of atoms) {{
        labelHandles.push(
          viewer.addLabel(atom.label, {{
            position: {{ x: atom.x, y: atom.y, z: atom.z }},
            fontColor: "#e5e7eb",
            backgroundColor: "rgba(15, 23, 42, 0.88)",
            borderColor: "#38bdf8",
            borderThickness: 1,
            inFront: true
          }})
        );
      }}
      viewer.render();
    }}

    function applyStyle() {{
      viewer.setStyle({{}}, styleConfig(currentStyle));
      syncLabels();
    }}

    function downloadBlob(filename, blob) {{
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 250);
    }}

    function downloadText(ext, content, mime = "text/plain;charset=utf-8") {{
      downloadBlob(`${{fileBase}}.${{ext}}`, new Blob([content], {{ type: mime }}));
    }}

    function formatXYZ() {{
      return xyzData + "\\n";
    }}

    function formatPDB() {{
      const lines = [
        `HEADER    openWFN viewer export`,
        `REMARK    Generated from openWFN`
      ];
      for (const atom of atoms) {{
        const serial = String(atom.serial).padStart(5, " ");
        const name = atom.elem.padStart(2, " ");
        const x = atom.x.toFixed(3).padStart(8, " ");
        const y = atom.y.toFixed(3).padStart(8, " ");
        const z = atom.z.toFixed(3).padStart(8, " ");
        const elem = atom.elem.padStart(2, " ");
        lines.push(`HETATM${{serial}} ${{name}}  MOL     1    ${{x}}${{y}}${{z}}  1.00  0.00          ${{elem}}`);
      }}
      for (const bond of bonds) {{
        const first = String(bond.i).padStart(5, " ");
        const second = String(bond.j).padStart(5, " ");
        lines.push(`CONECT${{first}}${{second}}`);
        lines.push(`CONECT${{second}}${{first}}`);
      }}
      lines.push("END");
      return lines.join("\\n") + "\\n";
    }}

    function formatSDF() {{
      const lines = [
        fileBase,
        "openWFN",
        "",
        `${{String(atoms.length).padStart(3, " ")}}${{String(bonds.length).padStart(3, " ")}}  0  0  0  0            999 V2000`
      ];
      for (const atom of atoms) {{
        const x = atom.x.toFixed(4).padStart(10, " ");
        const y = atom.y.toFixed(4).padStart(10, " ");
        const z = atom.z.toFixed(4).padStart(10, " ");
        const elem = atom.elem.padEnd(3, " ");
        lines.push(`${{x}}${{y}}${{z}} ${{elem}} 0  0  0  0  0  0  0  0  0  0  0  0`);
      }}
      for (const bond of bonds) {{
        const first = String(bond.i).padStart(3, " ");
        const second = String(bond.j).padStart(3, " ");
        const order = String(bond.order || 1).padStart(3, " ");
        lines.push(`${{first}}${{second}}${{order}}  0  0  0  0`);
      }}
      lines.push("M  END", "$$$$");
      return lines.join("\\n") + "\\n";
    }}

    function viewerCanvas() {{
      return document.querySelector("#viewer canvas");
    }}

    function pngDataUrl() {{
      if (typeof viewer.pngURI === "function") {{
        return viewer.pngURI();
      }}
      const canvas = viewerCanvas();
      return canvas ? canvas.toDataURL("image/png") : null;
    }}

    function downloadPNG() {{
      const uri = pngDataUrl();
      if (!uri) {{
        return;
      }}
      fetch(uri).then((res) => res.blob()).then((blob) => downloadBlob(`${{fileBase}}.png`, blob));
    }}

    function downloadJPEG() {{
      const uri = pngDataUrl();
      if (!uri) {{
        return;
      }}
      const img = new Image();
      img.onload = () => {{
        const canvas = document.createElement("canvas");
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext("2d");
        if (!ctx) {{
          return;
        }}
        ctx.fillStyle = "#111827";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0);
        canvas.toBlob((blob) => {{
          if (blob) {{
            downloadBlob(`${{fileBase}}.jpeg`, blob);
          }}
        }}, "image/jpeg", 0.94);
      }};
      img.src = uri;
    }}

    function downloadSVG() {{
      const uri = pngDataUrl();
      const canvas = viewerCanvas();
      if (!uri || !canvas) {{
        return;
      }}
      const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${{canvas.width}}" height="${{canvas.height}}" viewBox="0 0 ${{canvas.width}} ${{canvas.height}}">
  <rect width="100%" height="100%" fill="#111827"/>
  <image href="${{uri}}" width="${{canvas.width}}" height="${{canvas.height}}"/>
</svg>
`;
      downloadText("svg", svg, "image/svg+xml;charset=utf-8");
    }}

    viewer.addModel(xyzData, "xyz");
    applyStyle();
    viewer.zoomTo();
    viewer.render();

    styleButtons.forEach((button) => {{
      button.addEventListener("click", () => {{
        currentStyle = button.dataset.style;
        syncButtons();
        applyStyle();
      }});
    }});

    labelsToggle.addEventListener("click", () => {{
      labelsVisible = !labelsVisible;
      syncButtons();
      syncLabels();
    }});

    resetViewButton.addEventListener("click", () => {{
      viewer.zoomTo();
      viewer.render();
    }});

    downloadButtons.forEach((button) => {{
      button.addEventListener("click", () => {{
        const kind = button.dataset.download;
        if (kind === "xyz") {{
          downloadText("xyz", formatXYZ());
        }} else if (kind === "pdb") {{
          downloadText("pdb", formatPDB());
        }} else if (kind === "sdf") {{
          downloadText("sdf", formatSDF());
        }} else if (kind === "png") {{
          downloadPNG();
        }} else if (kind === "jpeg") {{
          downloadJPEG();
        }} else if (kind === "svg") {{
          downloadSVG();
        }}
      }});
    }});

    syncButtons();
  </script>
</body>
</html>
"""
    Path(filename).write_text(html, encoding="utf-8")
