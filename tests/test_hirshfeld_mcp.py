"""Hirshfeld parity checks for the optional read-only MCP adapter."""

import asyncio
import importlib.util
import shutil
from pathlib import Path

import pytest

import openwfn

pytestmark = pytest.mark.skipif(importlib.util.find_spec("mcp") is None, reason="MCP extra absent")


def test_mcp_hirshfeld_reuses_registered_result_without_hidden_defaults(tmp_path: Path) -> None:
    from mcp import Client

    from openwfn.mcp_server import create_server

    packaged = Path(openwfn.__file__).parent / "example_data/water.fchk"
    source = tmp_path / "water.fchk"
    shutil.copyfile(packaged, source)
    reference = openwfn.load(source).analyze("hirshfeld")

    async def check() -> None:
        async with Client(create_server(tmp_path)) as client:
            listing = await client.list_tools()
            assert all(tool.annotations.read_only_hint for tool in listing.tools)
            catalog = (await client.call_tool("list_analyses", {})).structured_content
            assert "hirshfeld" in catalog["analyses"]
            result = await client.call_tool(
                "run_analysis", {"path": "water.fchk", "analysis": "hirshfeld"}
            )
            assert not result.is_error
            record = result.structured_content
            assert record["analysis_name"] == "hirshfeld"
            assert record["analysis_version"] == "1"
            assert record["status"] == reference.status
            assert record["validation_status"] == reference.validation_status
            assert record["data"] == reference.data
            assert record["provenance"]["input_sha256"] == reference.provenance["input_sha256"]

    asyncio.run(check())
