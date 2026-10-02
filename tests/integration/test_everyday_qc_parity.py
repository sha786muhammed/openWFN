"""Registered analyses share numerical values through CLI/API/batch/report/MCP."""
import asyncio
import json
from pathlib import Path

import pytest

from openwfn.api import load
from openwfn.batch import run_batch
from openwfn.cli import main
from openwfn.reporting import build_report

WATER = Path(__file__).resolve().parents[2]/'examples/water/water.fchk'


@pytest.mark.parametrize('analysis, command', [('orbital-composition', ['orbitals', 'composition']), ('mayer', ['bondorder', 'mayer'])])
def test_registry_interfaces_have_identical_data(analysis, command, tmp_path, capsys):
    calc = load(WATER)
    reference = calc.analyze(analysis)
    assert main(['--format', 'json', str(WATER), *command]) == 0
    cli = json.loads(capsys.readouterr().out)
    assert cli['data'] == reference.data
    batch = run_batch([WATER], None, 1, tmp_path/'batch', analyses=(analysis,))
    assert batch.records[0].results[0].data == reference.data
    report = build_report(calc.data.calculation, (analysis,), tmp_path/'report.html', 'html', 'parity', {})
    text = report.read_text()
    manifest = json.loads(text.split('<script id="openwfn-report" type="application/json">')[1].split('</script>')[0])
    assert manifest['sections'][0]['data'] == reference.data
    # MCP captures its default stderr on import; use the real descriptor.
    with capsys.disabled():
        pytest.importorskip('mcp')
        from mcp import Client

    from openwfn.mcp_server import create_server

    async def check():
        async with Client(create_server(WATER.parent)) as client:
            result = await client.call_tool('run_analysis', {'path': WATER.name, 'analysis': analysis})
            assert result.structured_content['data'] == reference.data
    asyncio.run(check())
