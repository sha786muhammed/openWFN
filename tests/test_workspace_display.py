"""Human screens retain evidence without exposing implementation diagnostics."""

import io
import json
from pathlib import Path

import pytest
from rich.console import Console

from openwfn.app import CommandContext
from openwfn.guided import build_guided_session
from openwfn.presentation import render
from openwfn.results import ResultRecord

ROOT = Path(__file__).resolve().parents[1]


def test_compact_frontier_keeps_values_and_warning_without_dictionary_dump():
    record = ResultRecord(kind='frontier_orbitals', data={
        'spin': 'all', 'alpha': {'spin': 'restricted', 'homo_number': 13,
        'lumo_number': 14, 'homo_hartree': -.331537655,
        'lumo_hartree': .5497350542, 'gap_ev': 23.98065208}, 'beta': None,
        'reference_kind': 'restricted_closed_shell'}, warnings=('Source warning',))
    text = render(record, CommandContext(format='plain', compact=True))
    assert '-0.331537655 hartree' in text
    assert '23.98065208 eV' in text
    assert 'Source warning' in text
    assert "{'spin'" not in text
    assert 'Beta: Unavailable' not in text
    assert 'Analysis Validation Status:' not in text
    assert json.loads(render(record, CommandContext(format='json', compact=True)))['data']['beta'] is None


def test_compact_density_preserves_partial_and_conservation_evidence():
    record = ResultRecord(kind='density_integration', data={'electron_count': 26.42929161,
        'expected_electrons': 26., 'relative_error': .0165112158, 'spacing': .2,
        'padding': 6., 'density_kind': 'total'}, units={'electron_count': 'electron',
        'expected_electrons': 'electron', 'spacing': 'bohr', 'padding': 'bohr'},
        status='partial', validation_status='Experimental', warnings=('Conservation failed.',))
    text = render(record, CommandContext(format='plain', compact=True))
    assert '26.42929161 electron' in text and '1.6511%' in text
    assert 'partial' in text and 'Conservation failed.' in text
    assert '0.2 bohr' in text and '6.0 bohr' in text
    assert 'Experimental' not in text
    verbose = render(record, CommandContext(format='plain', compact=True, verbose=True))
    assert 'Experimental' in verbose


@pytest.mark.parametrize('width', [40, 80, 120])
def test_workspace_preserves_file_settings_and_path_at_each_width(width, tmp_path):
    from openwfn.workspace_display import print_workspace
    session = build_guided_session(ROOT / 'src/openwfn/example_data/everyday-qc/ethanol.molden')
    stream = io.StringIO()
    print_workspace(Console(file=stream, width=width, no_color=True), session,
        selected='density', title='Density / Integrate', description='Check electron count.',
        stage='Configure', settings=(('Grid spacing', '0.15 bohr'), ('Padding', '6 bohr')))
    output = stream.getvalue()
    assert 'ethanol.molden' in output and '0.15 bohr' in output
    assert 'Configure' in output
    # Rich may wrap inside a path; require every character, not one unbroken word.
    expected_path = str(session.directory / 'results')
    lines = output.splitlines()
    content_column = next(line.index('Density / Integrate') for line in lines
                          if 'Density / Integrate' in line)
    content = ''.join(''.join(line[content_column:].split()) for line in lines)
    assert ''.join(expected_path.split()) in content
    assert 'missing records' in output
    assert '\x1b' not in output
    assert all(len(line) <= width for line in output.splitlines())


def test_chat_uses_details_for_diagnostics_without_losing_partial_warning():
    from openwfn.assistant import AssistantAnswer
    from openwfn.assistant_display import render_chat_answer
    record = ResultRecord(kind='frontier_orbitals', data={
        'overall_homo_number': 13, 'overall_homo_hartree': -.331537655},
        status='partial', validation_status='Experimental', warnings=('Missing beta data.',))
    text = render_chat_answer(AssistantAnswer('', record), question='HOMO energy', source_label='test.wfx')
    assert 'partial' in text and 'Missing beta data.' in text
    assert 'Experimental' not in text and '/details' in text


def test_guided_result_details_retains_validation_and_provenance(monkeypatch, capsys):
    from openwfn import interactive
    choices = iter(['orbitals', 'exit'])
    navigation = iter(['details', 'home'])
    answers = iter(['frontier', 'alpha'])
    monkeypatch.setattr(interactive, 'prompt_workflow', lambda _: next(choices))
    monkeypatch.setattr(interactive, 'prompt_page_navigation', lambda _: next(navigation))
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    interactive.run_interactive(None, ROOT / 'examples/water/water.fchk')
    text = capsys.readouterr().out
    assert 'Choose → Configure → Run → Review → Save' in text
    assert 'Analysis Validation Status:' in text  # Only Details, not the compact initial answer.
    assert 'input_sha256' in text


def test_chat_details_and_model_aliases_are_available():
    from openwfn.terminal_ui import COMMANDS
    assert '/details' in COMMANDS and '/model' in COMMANDS


def test_compact_localization_never_presents_masked_zero_as_a_value():
    record = ResultRecord(kind='electron_localization_function', data={
        'points_bohr': [[.31, .47, .83], [8., 9., 10.]],
        'values': [.75, 0.], 'valid_mask': [True, False], 'channel': 'alpha'},
        units={'points_bohr': 'bohr', 'values': 'dimensionless'},
        validation_status='Experimental', warnings=('Low density at point 2.',))
    text = render(record, CommandContext(format='plain', compact=True))
    assert 'ELF (dimensionless)' in text
    assert 'Coordinates: bohr' in text
    assert '0.75' in text and 'Not defined' in text
    assert 'Low density at point 2.' in text
    assert 'valid_mask' not in text
    payload = json.loads(render(record, CommandContext(format='json', compact=True)))
    assert payload['data']['values'] == [.75, 0.]


def test_compact_realspace_table_preserves_units_and_full_arrays_in_json():
    record = ResultRecord(kind='density_derivatives', data={
        'points_bohr': [[.31, .47, .83]], 'rho': [.123], 'laplacian': [-.456],
        'gradient': [[1., 2., 3.]], 'hessian': [[[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]],
        'finite_mask': [True], 'channel': 'total'},
        units={'rho': 'electron/bohr^3', 'laplacian': 'electron/bohr^5'})
    text = render(record, CommandContext(format='plain', compact=True))
    assert 'electron/bohr^3' in text and 'electron/bohr^5' in text
    assert '0.123' in text and '-0.456' in text
    assert 'Hessian:' not in text
    assert json.loads(render(record, CommandContext(format='json', compact=True)))['data']['gradient'] == [[1., 2., 3.]]


def test_compact_populations_show_atom_numbers_instead_of_hidden_arrays():
    record = ResultRecord(kind='mulliken_population', data={
        'electron_populations': [8.3, .85, .85], 'atomic_charges': [-.3, .15, .15],
        'electron_count': 10., 'total_charge': 0., 'conservation_error': 0.},
        units={'electron_count': 'electron', 'total_charge': 'e', 'conservation_error': 'e'})
    text = render(record, CommandContext(format='plain', compact=True))
    assert 'Atom  Electron population (electron)  Charge (e)' in text
    assert '-0.30000000' in text and '0.15000000' in text
    assert 'Electron Count: 10.0 electron' in text
    assert 'Atomic Charges: [' not in text


def test_compact_qtaim_shows_points_and_never_implies_complete_topology():
    record = ResultRecord(kind='qtaim_topology', data={
        'critical_points': [{'position_bohr': [.1, .2, .3], 'rho': .25,
            'laplacian': -.4, 'label': '(3,-1)', 'hessian_eigenvalues': [-1., -1., 2.]}],
        'search_complete': False, 'bond_paths': [], 'seed_count': 1,
        'settings': {'max_iterations': 96}}, status='partial', validation_status='Experimental',
        warnings=('Search is bounded and not exhaustive.',))
    text = render(record, CommandContext(format='plain', compact=True))
    assert '(3,-1)' in text and '0.25' in text
    assert 'Coordinates: bohr' in text and 'electron/bohr^3' in text
    assert 'partial' in text and 'not exhaustive' in text
    assert "{'position_bohr'" not in text and 'max_iterations' not in text
    assert json.loads(render(record, CommandContext(format='json')))['data']['settings']['max_iterations'] == 96


def test_compact_nto_displays_weights_without_internal_dictionary_dump():
    record = ResultRecord(kind='natural_transition_orbitals', data={
        'job': 1, 'state': 2, 'spin_block': 'restricted',
        'pairs': [{'pair': 1, 'weight': .9, 'cumulative_weight': .9,
                   'singular_value': .8, 'hole_norm_residual': 1e-12}],
        'omitted_pair_count': 1}, validation_status='Experimental',
        warnings=('One pair omitted by the weight filter.',))
    text = render(record, CommandContext(format='plain', compact=True))
    assert 'Weight (%)' in text and '90.0000' in text
    assert 'Job: 1' in text and 'State: 2' in text
    assert 'One pair omitted' in text and "{'pair'" not in text
    assert json.loads(render(record, CommandContext(format='json')))['data']['pairs'][0]['weight'] == .9
