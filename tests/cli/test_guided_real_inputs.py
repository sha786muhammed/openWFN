"""Guided terminal workflows use the same normalized real inputs as the API."""
from pathlib import Path

import pytest

from openwfn import interactive

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('name', ['water', 'oxygen_triplet', 'ammonium_cation'])
def test_molden_guided_orbitals(name, monkeypatch, capsys):
    pytest.importorskip('iodata')
    workflows = iter(['orbitals', 'exit'])
    monkeypatch.setattr(interactive, 'prompt_workflow', lambda: next(workflows))
    monkeypatch.setattr(interactive, 'prompt_page_navigation', lambda _: 'back')
    interactive.run_interactive(None, ROOT/f'examples/everyday-qc/{name}.molden')
    output = capsys.readouterr().out
    assert 'Homo' in output
    assert 'Lumo' in output
    assert 'Analysis Validation Status:' in output
    assert 'Result Status: success' in output
