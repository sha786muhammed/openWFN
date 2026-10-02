"""Human output is bounded and scientific tables retain units and status."""
import json

from openwfn.app import CommandContext
from openwfn.presentation import render
from openwfn.results import ResultRecord


def test_long_spectrum_arrays_are_abbreviated_only_in_human_output():
    record = ResultRecord(kind='orbital_dos', data={'energy_ev': list(range(1000))})
    human = render(record, CommandContext(format='plain'))
    assert len(human) < 300
    assert '1000 entries' in human
    assert len(json.loads(render(record, CommandContext(format='json')))['data']['energy_ev']) == 1000


def test_composition_has_readable_atom_table_and_method():
    record = ResultRecord(kind='orbital_composition', data={'method': 'lowdin', 'atom_contributions': [
        {'atom_number': 1, 'atomic_number': 8, 'percent': 70.25}]}, validation_status='Validated')
    text = render(record, CommandContext(format='plain'))
    assert 'Atom  Element  Contribution (%)' in text
    assert '70.2500' in text
    assert 'Method: lowdin' in text
    assert 'Analysis Validation Status: Validated' in text
