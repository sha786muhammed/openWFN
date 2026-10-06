"""Guided terminal workflows use the same normalized real inputs as the API."""
from pathlib import Path

import pytest

from openwfn import interactive

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('name', ['water', 'oxygen_triplet', 'ammonium_cation'])
def test_molden_guided_orbitals(name, monkeypatch, capsys):
    pytest.importorskip('iodata')
    workflows = iter(['orbitals', 'exit'])
    monkeypatch.setattr('builtins.input', lambda _: '')
    monkeypatch.setattr(interactive, 'prompt_workflow', lambda _: next(workflows))
    monkeypatch.setattr(interactive, 'prompt_page_navigation', lambda _: 'back')
    interactive.run_interactive(None, ROOT/f'examples/everyday-qc/{name}.molden')
    output = capsys.readouterr().out
    assert 'Homo' in output
    assert 'Lumo' in output
    assert 'Analysis Validation Status:' in output
    assert 'Result Status: success' in output


@pytest.mark.parametrize(('workflow', 'answers', 'expected'), [
    ('summary', [], 'Summary'),
    ('orbitals', ['composition', 'beta', 'homo', 'lowdin'], 'Contribution (%)'),
    ('orbitals', ['dos', 'all'], 'entries (use'),
    ('orbitals', ['pdos', 'all'], 'Projection Method: lowdin'),
    ('bonds', ['mayer'], 'Mayer bond order'),
    ('density', ['esp', '1.127 1.434 1.741', 'total'], 'Method: integrals'),
])
def test_guided_shared_real_analysis(workflow, answers, expected, monkeypatch, capsys):
    pytest.importorskip('iodata')
    workflows = iter([workflow, 'exit'])
    inputs = iter(answers)
    monkeypatch.setattr(interactive, 'prompt_workflow', lambda _: next(workflows))
    monkeypatch.setattr(interactive, 'prompt_page_navigation', lambda _: 'back')
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))
    interactive.run_interactive(None, ROOT/'examples/everyday-qc/oh_diffuse_uhf.molden')
    output = capsys.readouterr().out
    assert expected in output
    assert 'Result Status: success' in output


def test_bad_guided_point_returns_structured_failure_and_navigation(monkeypatch, capsys):
    pytest.importorskip('iodata')
    workflows = iter(['density', 'exit'])
    inputs = iter(['esp', 'invalid coordinates'])
    monkeypatch.setattr(interactive, 'prompt_workflow', lambda _: next(workflows))
    monkeypatch.setattr(interactive, 'prompt_page_navigation', lambda _: 'back')
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))
    interactive.run_interactive(None, ROOT/'examples/everyday-qc/water.molden')
    text = capsys.readouterr().out
    assert 'Result Status: failed' in text
    assert 'Error:' in text
    assert 'Exiting openWFN.' in text


def test_invalid_cube_mo_keeps_guided_session_alive(tmp_path, monkeypatch, capsys):
    pytest.importorskip('iodata')
    output = tmp_path/'invalid.cube'
    workflows = iter(['orbitals', 'exit'])
    inputs = iter(['cube', 'alpha', '999999', str(output), 'yes'])
    monkeypatch.setattr(interactive, 'prompt_workflow', lambda _: next(workflows))
    monkeypatch.setattr(interactive, 'prompt_page_navigation', lambda _: 'back')
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))
    interactive.run_interactive(None, ROOT/'examples/everyday-qc/water.molden')
    text = capsys.readouterr().out
    assert 'Result Status: failed' in text
    assert 'Exiting openWFN.' in text
    assert not output.exists()
