import json
import shlex
from pathlib import Path

import pytest

from openwfn import interactive
from openwfn.guided import build_guided_session

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / 'examples/water/water.fchk'


def test_command_preserves_spaces_and_format_hint(tmp_path):
    from openwfn.guided import reproducible_command
    source = tmp_path / 'water β.molden.input'
    source.write_text((ROOT / 'tests/fixtures/interop/molden/water.molden').read_text())
    session = build_guided_session(source, format_hint='molden')
    command = reproducible_command(session, arguments=('orbitals', 'frontier', '--spin', 'alpha'))
    assert shlex.split(command) == ['openwfn', '--input-format', 'molden', str(source),
                                  'orbitals', 'frontier', '--spin', 'alpha']


def test_interrupted_export_preserves_existing_output(tmp_path):
    from openwfn.guided_exports import OutputDestination, export_atomically
    output = tmp_path / 'result.json'
    output.write_text('original')
    def interrupted(stage):
        stage.write_text('incomplete')
        raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        export_atomically(OutputDestination(output, overwrite=True), interrupted)
    assert output.read_text() == 'original'
    assert list(tmp_path.iterdir()) == [output]


def test_result_menu_saves_complete_json(tmp_path, monkeypatch, capsys):
    workflows = iter(['orbitals', 'exit'])
    navigation = iter(['command', 'details', 'save-json', 'home'])
    output = tmp_path / 'frontier'
    answers = iter(['frontier', 'alpha', str(output), 'yes'])
    monkeypatch.setattr(interactive, 'prompt_workflow', lambda _: next(workflows))
    monkeypatch.setattr(interactive, 'prompt_page_navigation', lambda _: next(navigation))
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    interactive.run_interactive(None, WATER)
    record = json.loads(output.with_suffix('.json').read_text())
    assert record['kind'] == 'frontier_orbitals'
    assert record['status'] == 'success'
    assert record['units']['gap_ev'] == 'eV'
    assert len(record['provenance']['input_sha256']) == 64
    terminal = capsys.readouterr().out
    assert 'orbitals frontier --spin alpha' in terminal
    assert str(output.with_suffix('.json')) in terminal


def test_basename_export_is_under_session_results(tmp_path, monkeypatch):
    from dataclasses import replace
    session = replace(build_guided_session(WATER), directory=tmp_path)
    answers = iter(['dvb', 'yes'])
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    destination = interactive.confirm_output_path(session, 'report', '.html')
    assert destination.path == tmp_path / 'results/dvb.html'
    assert destination.overwrite is False


def test_structure_export_displays_final_path_not_staging_path(tmp_path, monkeypatch, capsys):
    workflows = iter(['export', 'exit'])
    answers = iter([str(tmp_path / 'structure'), 'yes'])
    monkeypatch.setattr(interactive, 'prompt_workflow', lambda _: next(workflows))
    monkeypatch.setattr(interactive, 'prompt_page_navigation', lambda _: 'home')
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    interactive.run_interactive(None, WATER)
    assert (tmp_path / 'structure.xyz').read_text().splitlines()[0] == '3'
    assert '.openwfn-export-' not in capsys.readouterr().out


def test_property_command_omits_wavefunction_reader_hint():
    from dataclasses import replace

    from openwfn.guided import reproducible_command
    session = replace(build_guided_session(WATER), format_hint='gaussianlog')
    tokens = shlex.split(reproducible_command(session, arguments=('properties',)))
    assert tokens == ['openwfn', str(WATER), 'properties']


def test_population_result_can_be_saved_as_csv(tmp_path, monkeypatch, capsys):
    workflows = iter(['population', 'exit'])
    navigation = iter(['save-csv', 'home'])
    output = tmp_path / 'charges.csv'
    answers = iter(['mulliken', str(output), 'yes'])
    monkeypatch.setattr(interactive, 'prompt_workflow', lambda _: next(workflows))
    monkeypatch.setattr(interactive, 'prompt_page_navigation', lambda _: next(navigation))
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    interactive.run_interactive(None, WATER)
    assert output.is_file(), capsys.readouterr().out
    assert 'atomic_charges' in output.read_text()


def test_guided_spectrum_can_save_csv_with_selected_curve_settings(tmp_path, monkeypatch):
    import csv
    workflows = iter(['methods', 'exit'])
    navigation = iter(['save-csv', 'home'])
    output = tmp_path / 'IR curve β.csv'
    answers = iter(['ir-spectrum', '12', '1000', '4500', '321', 'run', str(output), 'yes'])
    monkeypatch.setattr(interactive, 'prompt_workflow', lambda _: next(workflows))
    monkeypatch.setattr(interactive, 'prompt_page_navigation', lambda _: next(navigation))
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    interactive.run_interactive(None, ROOT / 'tests/fixtures/gaussian/vibrations/water_freq.log')
    with output.open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 321
    assert float(rows[0]['frequency_cm1']) == 1000
    assert float(rows[-1]['frequency_cm1']) == 4500


def test_atomic_overwrite_preserves_private_output_permissions(tmp_path):
    import os
    import stat
    if os.name == 'nt':
        pytest.skip('POSIX output permissions')
    from openwfn.guided_exports import OutputDestination, export_atomically
    destination = tmp_path / 'private.json'
    destination.write_text('old')
    destination.chmod(0o600)
    export_atomically(OutputDestination(destination, overwrite=True),
                     lambda stage: stage.write_text('new'))
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
