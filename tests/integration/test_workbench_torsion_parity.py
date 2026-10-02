"""Signed JS torsions follow the established core convention in both senses."""
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from openwfn.geometry import dihedral
from openwfn.parsers.gaussian.fchk import parse_fchk
from openwfn.workbench.export import export_workbench

ROOT = Path(__file__).resolve().parents[2]


def test_signed_javascript_torsions_match_core(tmp_path):
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node is optional; full interactive Chromium parity runs in CI')
    path = export_workbench(parse_fchk(ROOT/'examples/water/water.fchk'), tmp_path/'workbench.html')
    text = path.read_text()
    start, end = text.index('function vector('), text.index('function resetMeasurement(')
    javascript = text[start:end]
    points = np.random.default_rng(731).normal(size=(100, 4, 3)).tolist()
    script = javascript+'\nconsole.log(JSON.stringify('+json.dumps(points)+'.map(p=>calculateDihedral(...p))));'
    values = json.loads(subprocess.check_output([node], input=script, text=True))
    expected = [dihedral(1, 2, 3, 4, coordinates) for coordinates in points]
    assert min(expected) < -90 and max(expected) > 90
    assert values == pytest.approx(expected, abs=1e-10)
