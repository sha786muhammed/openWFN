"""Scientific records agree across interfaces; not an independent value reference."""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

from openwfn import load
from openwfn.assistant import AnalysisPlan, AssistantSession
from openwfn.assistant_display import render_chat_answer

ROOT = Path(__file__).resolve().parents[1]
ETHANOL = 'examples/everyday-qc/ethanol.molden'
CASES = [
    ('examples/water/water.fchk', 'summary', {}, ('summary',)),
    (ETHANOL, 'frontier-all', {}, ('orbitals', 'frontier', '--spin', 'all')),
    ('tests/fixtures/interop/wfn/water.wfn', 'frontier', {}, ('orbitals', 'frontier')),
    ('tests/fixtures/interop/wfx/water.wfx', 'mulliken', {}, ('population', 'mulliken')),
    ('tests/fixtures/interop/mwfn/water.mwfn', 'lowdin', {}, ('population', 'lowdin')),
    (ETHANOL, 'hirshfeld', {}, ('population', 'hirshfeld')),
    (ETHANOL, 'mayer', {'threshold': .9}, ('bondorder', 'mayer', '--threshold', '.9')),
    (ETHANOL, 'orbital-composition', {'mo': 'lumo', 'method': 'lowdin'},
        ('orbitals', 'composition', '--mo', 'lumo', '--method', 'lowdin')),
    (ETHANOL, 'dos', {'points': 401, 'energy_min_ev': -30., 'energy_max_ev': 30.},
        ('orbitals', 'dos', '--points', '401', '--energy-min', '-30', '--energy-max', '30')),
    ('tests/fixtures/gaussian/vibrations/water_freq.log', 'ir-spectrum',
        {'fwhm_cm1': 12., 'points': 321}, ('spectra', 'ir', '--fwhm', '12', '--points', '321')),
    ('tests/fixtures/gaussian/vibrations/water_freq.log', 'normal-mode',
        {'mode': 2}, ('vibrations', 'mode', '2')),
]
CASES += [(ETHANOL, method, {'x_bohr': .21, 'y_bohr': .37, 'z_bohr': .29,
                            **({'channel': 'total'} if method in {'elf', 'lol'} else {})}, None)
          for method in ('density-derivatives', 'kinetic-energy-density', 'elf', 'lol', 'nci')]


def assert_same_scientific_record(observed, expected):
    for key in ('data', 'units', 'status', 'warnings', 'validation_status', 'provenance', 'schema_version'):
        assert observed[key] == expected[key], key


@pytest.mark.parametrize('method,parameters,command', [
    ('density', {'spacing_bohr': .4, 'padding_bohr': 3.},
     ('density', 'integrate', '--spacing', '.4', '--padding', '3')),
    ('geometry_distance', {'atom_i': 1, 'atom_j': 2}, ('dist', '1', '2')),
    ('esp', {'coordinates_angstrom': (4., 4., 4.)}, ('esp', 'point', '4', '4', '4')),
])
def test_direct_service_cli_api_parity(method, parameters, command):
    pytest.importorskip('iodata')
    path = ROOT / ETHANOL
    expected = getattr(load(path), method)(**parameters).as_dict()
    completed = subprocess.run([sys.executable, '-m', 'openwfn.cli', '--format', 'json',
        str(path), *command], capture_output=True, text=True, cwd=ROOT)
    assert completed.returncode == 0, completed.stderr + completed.stdout
    assert_same_scientific_record(json.loads(completed.stdout), expected)


@pytest.mark.parametrize('source,method,parameters,command', CASES,
                         ids=[f'{Path(case[0]).suffix}-{case[1]}' for case in CASES])
def test_scientific_record_parity(source, method, parameters, command):
    pytest.importorskip('iodata')
    pytest.importorskip('mcp')
    from mcp import Client

    from openwfn.mcp_server import create_server

    path = ROOT / source
    engine_parameters = dict(parameters)
    if 'x_bohr' in parameters:
        engine_parameters = {key: value for key, value in parameters.items()
                             if key not in {'x_bohr', 'y_bohr', 'z_bohr'}}
        engine_parameters['points_bohr'] = [[parameters[key] for key in ('x_bohr', 'y_bohr', 'z_bohr')]]
    expected = load(path).analyze(method, **engine_parameters).as_dict()
    assistant = AssistantSession(path, data_root=ROOT)
    assert assistant.model_context()['analyses'][method]['available']
    answer = assistant.execute(AnalysisPlan('analysis', method, parameters))
    assert answer.record is not None
    assert_same_scientific_record(answer.record.as_dict(), expected)
    shown = render_chat_answer(answer, question=method, source_label=path.name)
    assert path.name in shown
    for warning in expected['warnings']:
        assert warning in shown

    async def check_mcp():
        async with Client(create_server(ROOT)) as client:
            inspected = await client.call_tool('inspect_file', {'path': source})
            assert inspected.structured_content['data']['analyses'][method]['available']
            result = await client.call_tool('run_analysis', {
                'path': source, 'analysis': method, 'parameters': parameters})
            assert not result.is_error
            assert_same_scientific_record(result.structured_content, expected)
    asyncio.run(check_mcp())
    if command is not None:
        completed = subprocess.run([sys.executable, '-m', 'openwfn.cli', '--format', 'json',
            str(path), *command], capture_output=True, text=True, cwd=ROOT)
        assert completed.returncode == 0, completed.stderr + completed.stdout
        assert_same_scientific_record(json.loads(completed.stdout), expected)


def test_missing_spectrum_stays_unavailable_in_assistant_and_mcp():
    pytest.importorskip('mcp')
    from mcp import Client

    from openwfn.mcp_server import create_server

    source = 'examples/ammonia/ammonia.xyz'
    assistant = AssistantSession(ROOT / source, data_root=ROOT)
    assert not assistant.model_context()['analyses']['ir-spectrum']['available']
    answer = assistant.execute(AnalysisPlan('analysis', 'ir-spectrum'))
    assert answer.record.status == 'failed'
    assert answer.record.error.category == 'DataUnavailableError'
    assert answer.record.data == {}
    shown = render_chat_answer(answer, question='IR spectrum', source_label='ammonia.xyz')
    assert 'Not available from this file.' in shown

    async def check_mcp():
        async with Client(create_server(ROOT)) as client:
            result = await client.call_tool('run_analysis', {'path': source, 'analysis': 'ir-spectrum'})
            record = result.structured_content
            assert record['status'] == 'failed'
            assert record['error']['category'] == 'DataUnavailableError'
            assert record['data'] == {}
    asyncio.run(check_mcp())
