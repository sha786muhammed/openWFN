"""Execute the actual CI offline check with local SVG and network-resource fixtures."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from openwfn.branding import wordmark_svg

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('external_image', [False, True])
def test_ci_offline_check_distinguishes_svg_namespace_from_network_resource(tmp_path, external_image):
    workflow = (ROOT / '.github/workflows/tests.yml').read_text()
    block = workflow.split('  wheel-smoke:\n', 1)[1].split('  interop-wheel-smoke:\n', 1)[0]
    body = block.split("wheel-test/bin/python - <<'PY'\n", 1)[1].split('\n          PY', 1)[0]
    script = '\n'.join(line[10:] for line in body.splitlines())
    (tmp_path / 'summary.json').write_text(json.dumps({'status': 'success', 'data': {'formula': 'H2O'}}))
    report = wordmark_svg()
    if external_image:
        report += '<img src="https://example.invalid/image.png">'
    (tmp_path / 'report.html').write_text(report)
    (tmp_path / 'workbench.html').write_text('Molecular rendering: 3Dmol.js (BSD-3-Clause)')
    (tmp_path / 'workbench.txt').write_text('Analysis Validation Status: Stable')
    completed = subprocess.run([sys.executable, '-c', script], cwd=tmp_path, capture_output=True)
    assert (completed.returncode == 0) is (not external_image), completed.stderr.decode()
