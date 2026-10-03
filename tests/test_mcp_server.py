"""Protocol-level checks for the optional, read-only MCP adapter."""

import asyncio
import importlib.util
import os
import shutil
import sys
from pathlib import Path

import pytest

import openwfn

pytestmark = pytest.mark.skipif(importlib.util.find_spec("mcp") is None, reason="MCP extra absent")


def test_mcp_adapter_exists():
    assert importlib.util.find_spec("openwfn.mcp_server") is not None


@pytest.fixture
def inputs(tmp_path):
    source = Path(openwfn.__file__).parent / "example_data/water.fchk"
    shutil.copyfile(source, tmp_path / "water molecule.fchk")
    vibrations = Path(__file__).parent / "fixtures/gaussian/vibrations/water_freq.log"
    shutil.copyfile(vibrations, tmp_path / "water_freq.log")
    return tmp_path


def test_tools_preserve_results_and_reject_unsafe_paths(inputs, tmp_path):
    from mcp import Client

    from openwfn.mcp_server import create_server

    outside = tmp_path.parent / f"{tmp_path.name}-outside.fchk"
    outside.write_text("not a wavefunction")
    (inputs / "escape.fchk").symlink_to(outside)

    async def check():
        async with Client(create_server(inputs)) as client:
            listing = await client.list_tools()
            assert {tool.name for tool in listing.tools} == {
                "inspect_file", "list_analyses", "run_analysis", "output_properties"
            }
            assert all(tool.annotations.read_only_hint for tool in listing.tools)
            catalog = (await client.call_tool("list_analyses", {})).structured_content
            assert {
                "summary", "vibrations", "ir-spectrum", "raman-spectrum", "normal-mode"
            }.issubset(catalog["analyses"])
            inspection = await client.call_tool("inspect_file", {"path": "water molecule.fchk"})
            assert inspection.structured_content["data"]["analyses"]["summary"]["available"]
            result = await client.call_tool("run_analysis", {
                "path": "water molecule.fchk", "analysis": "summary"
            })
            record = result.structured_content
            assert record["status"] == "success"
            assert record["data"]["formula"] == "H2O"
            assert record["data"]["atoms"] == 3
            assert record["schema_version"] == "1.0"
            assert record["provenance"]["input_sha256"]
            frontier = await client.call_tool("run_analysis", {
                "path": "water molecule.fchk", "analysis": "frontier"
            })
            assert frontier.structured_content["units"]["gap_ev"] == "eV"
            unknown = await client.call_tool("run_analysis", {
                "path": "water molecule.fchk", "analysis": "invented"
            })
            assert unknown.structured_content["status"] == "failed"
            assert unknown.structured_content["error"]["category"] == "ValueError"
            for path in (str(outside), "../" + outside.name, "escape.fchk", ".", "missing"):
                rejected = await client.call_tool("inspect_file", {"path": path})
                assert rejected.is_error

    asyncio.run(check())


def test_mcp_spectroscopy_parameters_match_python_api(inputs):
    from mcp import Client

    from openwfn.mcp_server import create_server

    python_ir = openwfn.load(inputs / "water_freq.log").analyze(
        "ir-spectrum", fwhm_cm1=12.0, points=321
    )
    python_mode = openwfn.load(inputs / "water_freq.log").analyze("normal-mode", mode=2)

    async def check():
        async with Client(create_server(inputs)) as client:
            ir = await client.call_tool(
                "run_analysis",
                {
                    "path": "water_freq.log",
                    "analysis": "ir-spectrum",
                    "parameters": {"fwhm_cm1": 12.0, "points": 321},
                },
            )
            assert not ir.is_error
            ir_record = ir.structured_content
            assert ir_record["status"] == "success"
            assert ir_record["data"] == python_ir.data
            assert ir_record["units"] == python_ir.units
            assert ir_record["validation_status"] == python_ir.validation_status
            assert ir_record["warnings"] == list(python_ir.warnings)
            assert ir_record["provenance"] == python_ir.provenance

            mode = await client.call_tool(
                "run_analysis",
                {
                    "path": "water_freq.log",
                    "analysis": "normal-mode",
                    "parameters": {"mode": 2},
                },
            )
            assert not mode.is_error
            mode_record = mode.structured_content
            assert mode_record["data"] == python_mode.data
            assert mode_record["units"] == python_mode.units
            assert mode_record["provenance"] == python_mode.provenance

    asyncio.run(check())


def test_mcp_analysis_parameters_reject_nested_values(inputs):
    from mcp import Client

    from openwfn.mcp_server import create_server

    async def check():
        async with Client(create_server(inputs)) as client:
            result = await client.call_tool(
                "run_analysis",
                {
                    "path": "water_freq.log",
                    "analysis": "ir-spectrum",
                    "parameters": {"points": {"nested": 321}},
                },
            )
            assert result.is_error or result.structured_content["status"] == "failed"

    asyncio.run(check())


def test_stdio_roundtrip(inputs):
    from mcp import Client, StdioServerParameters

    async def check():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "openwfn.mcp_server", "--data-root", str(inputs)],
            env=dict(os.environ),
        )
        async with Client(params) as client:
            result = await client.call_tool("run_analysis", {
                "path": "water molecule.fchk", "analysis": "summary"
            })
            assert not result.is_error
            assert result.structured_content["data"]["formula"] == "H2O"

    asyncio.run(check())


def test_file_size_limit(inputs):
    from mcp import Client

    from openwfn.mcp_server import create_server

    async def check():
        async with Client(create_server(inputs, max_file_bytes=1)) as client:
            result = await client.call_tool("inspect_file", {"path": "water molecule.fchk"})
            assert result.is_error

    asyncio.run(check())


def test_checkpoint_is_rejected_even_with_existing_sidecar(inputs):
    from mcp import Client

    from openwfn.mcp_server import create_server

    (inputs / "binary.CHK").write_bytes(b"binary checkpoint placeholder")
    shutil.copyfile(inputs / "water molecule.fchk", inputs / "binary.fchk")

    async def check():
        async with Client(create_server(inputs)) as client:
            for tool, arguments in (
                ("inspect_file", {"path": "binary.CHK"}),
                ("inspect_file", {"path": "binary.CHK", "format_hint": "fchk"}),
                ("run_analysis", {"path": "binary.CHK", "analysis": "summary"}),
                ("output_properties", {"path": "binary.CHK"}),
            ):
                result = await client.call_tool(tool, arguments)
                assert result.is_error
                assert any(".fchk" in item.text for item in result.content)

    asyncio.run(check())


def test_invalid_configuration(inputs):
    from openwfn.mcp_server import create_server

    with pytest.raises(ValueError):
        create_server(inputs / "missing")
    with pytest.raises(ValueError):
        create_server(inputs, max_file_bytes=0)


def test_malformed_file_returns_failed_record(inputs):
    from mcp import Client

    from openwfn.mcp_server import create_server

    (inputs / "bad.fchk").write_text("This is not a formatted checkpoint")

    async def check():
        async with Client(create_server(inputs)) as client:
            result = await client.call_tool("run_analysis", {
                "path": "bad.fchk", "analysis": "summary"
            })
            assert result.structured_content["status"] == "failed"
            assert result.structured_content["data"] == {}
            assert result.structured_content["error"]["category"]

    asyncio.run(check())


@pytest.mark.skipif(
    importlib.util.find_spec("iodata") is None or importlib.util.find_spec("cclib") is None,
    reason="Output-reader integration requires interop and outputs extras",
)
def test_real_orca_output_properties(inputs):
    import iodata
    from mcp import Client

    from openwfn.mcp_server import create_server

    source = Path(iodata.__file__).parent / "test/data/orca_gradient.out"
    if not source.is_file():
        pytest.skip("IOData distribution does not include the ORCA fixture")
    shutil.copyfile(source, inputs / "orca.out")

    async def check():
        async with Client(create_server(inputs)) as client:
            result = await client.call_tool("output_properties", {"path": "orca.out"})
            record = result.structured_content
            assert record["status"] == "success"
            assert record["data"]["atom_count"] == 32
            assert record["data"]["charge"] == 0
            assert record["data"]["multiplicity"] == 1
            assert record["data"]["scf_energy_hartree"] == pytest.approx(
                -742.985592886484, abs=1e-8
            )
            assert record["provenance"]["input_sha256"]

    asyncio.run(check())
