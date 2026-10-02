"""Resource and parameter safeguards must fail before expensive work."""
import asyncio
from pathlib import Path

import pytest

from openwfn.api import load

WATER = Path(__file__).resolve().parents[2]/'examples/water/water.fchk'


def test_registry_summary_does_not_silently_ignore_unknown_parameters(tmp_path):
    source = tmp_path/"h.xyz"
    source.write_text("1\nstructure only\nH 0 0 0\n")
    with pytest.raises(TypeError):
        load(source).analyze('summary', invented_parameter=True)


def test_mcp_dense_ao_limit_preserves_readonly_and_cheap_analyses():
    pytest.importorskip('mcp')
    from mcp import Client

    from openwfn.mcp_server import create_server

    async def check():
        async with Client(create_server(WATER.parent, max_basis_functions=2)) as client:
            for name in ('mayer', 'orbital-composition', 'pdos', 'mulliken', 'lowdin'):
                record = (await client.call_tool('run_analysis', {'path': WATER.name, 'analysis': name})).structured_content
                assert record['status'] == 'failed'
                assert 'AO resource limit' in record['error']['message']
            summary = (await client.call_tool('run_analysis', {'path': WATER.name, 'analysis': 'summary'})).structured_content
            assert summary['status'] == 'success'
    asyncio.run(check())
