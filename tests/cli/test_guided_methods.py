from pathlib import Path

import pytest

from openwfn.guided import available_workflows, build_guided_session

ROOT = Path(__file__).resolve().parents[2]


def run_method(session, name, answers):
    try:
        from openwfn.guided_methods import run_guided_method
    except ImportError:
        pytest.fail('Guided registered-analysis access is missing')
    sequence = iter(answers)
    return run_guided_method(session, name, ask=lambda prompt: next(sequence))


def test_all_methods_remain_discoverable_from_structure_only_input():
    session = build_guided_session(ROOT / 'examples/ammonia/ammonia.xyz')
    assert 'methods' in {choice.command for choice in available_workflows(session)}
    record = run_method(session, 'ir-spectrum', [])
    assert record.status == 'failed'
    assert record.error.category == 'DataUnavailableError'
    assert 'IR intensities' in record.error.message


def test_guided_mayer_respects_threshold_and_review_cancel():
    session = build_guided_session(ROOT / 'examples/everyday-qc/ethanol.molden')
    record = run_method(session, 'mayer', ['0.9', 'run'])
    assert record.status == 'success'
    assert record.data['threshold'] == .9
    assert run_method(session, 'mayer', ['0.9', 'back']) is None


def test_open_shell_field_requires_explicit_valid_channel_and_keeps_bohr_units():
    session = build_guided_session(ROOT / 'examples/everyday-qc/oxygen_triplet.molden')
    record = run_method(session, 'elf', ['.31 .47 .83', 'alpha', 'run'])
    assert record.status == 'success'
    assert record.units['points_bohr'] == 'bohr'
    assert record.data['points_bohr'] == [[.31, .47, .83]]
    invalid = run_method(session, 'elf', ['.31 .47 .83', 'anything', 'run'])
    assert invalid.status == 'failed'
    assert invalid.error.category == 'ValueError'


def test_guided_excitation_selects_job_instead_of_merging_calculations():
    from dataclasses import replace

    from openwfn.api import OpenWFNCalculation
    from openwfn.data import wrap_calculation
    from openwfn.excited_states import ExcitedState, ExcitedStateCollection, ExcitedStateJob

    session = build_guided_session(ROOT / 'examples/water/water.fchk')
    jobs = tuple(ExcitedStateJob(index=index, source_program='Gaussian', method_family='tddft', method_detail='TD(B3LYP)',
                                states=(ExcitedState(index=1, source_state='1', energy_ev=energy),))
                 for index, energy in ((1, 4.), (2, 6.)))
    data = session.data.calculation
    updated = replace(data, records={**data.records, 'excited_states': ExcitedStateCollection(jobs)})
    session = replace(session, calculation=OpenWFNCalculation(wrap_calculation(updated)))
    result = run_method(session, 'excited-state', ['1', '2', 'run'])
    assert result.status == 'success'
    assert result.data['job'] == 2
    assert result.data['energy_ev'] == 6.


def test_guided_dos_has_bounded_energy_range_and_point_count():
    session = build_guided_session(ROOT / 'examples/everyday-qc/ethanol.molden')
    result = run_method(session, 'dos', ['all', '.3', '-30', '30', '401', 'run'])
    assert result.status == 'partial'  # This window excludes deep core orbitals.
    assert result.warnings
    assert len(result.data['energy_ev']) == 401
    assert result.data['energy_ev'][0] == -30.
    assert result.data['energy_ev'][-1] == 30.


def test_method_groups_cover_registry_once_and_explain_absent_records():
    from openwfn.analysis.registry import available_analyses
    from openwfn.guided_methods import method_groups

    session = build_guided_session(ROOT / 'examples/ammonia/ammonia.xyz')
    groups = method_groups(session)
    methods = [item for _, choices in groups for item in choices]
    assert sorted(item.command for item in methods) == sorted(available_analyses())
    ir = next(item for item in methods if item.command == 'ir-spectrum')
    assert 'IR intensities' in ir.label
    assert 'unavailable' in ir.label


def test_guided_ir_respects_frequency_window_and_curve_points():
    session = build_guided_session(ROOT / 'tests/fixtures/gaussian/vibrations/water_freq.log')
    result = run_method(session, 'ir-spectrum', ['12', '1000', '4500', '321', 'run'])
    assert result.status == 'success'
    assert result.data['broadening']['fwhm_cm1'] == 12
    assert len(result.data['frequency_cm1']) == 321
    assert result.data['frequency_cm1'][0] == 1000
    assert result.data['frequency_cm1'][-1] == 4500


def test_guided_hirshfeld_records_selected_quadrature():
    session = build_guided_session(ROOT / 'examples/everyday-qc/methane.molden')
    result = run_method(session, 'hirshfeld', ['48', '10', '20', '16', 'run'])
    assert result.status in {'success', 'partial'}
    assert result.data['quadrature']['radial_points'] == 48
    assert result.data['quadrature']['theta_points'] == 10
    assert result.data['quadrature']['phi_points'] == 20
    assert result.data['quadrature']['radial_extent_bohr'] == 16
    assert sum(atom['electron_population'] for atom in result.data['atoms']) > 9


def test_guided_qtaim_respects_explicit_seed_and_iteration_limit():
    session = build_guided_session(ROOT / 'examples/everyday-qc/ethanol.molden')
    result = run_method(session, 'qtaim', ['.31 .47 .83', '8', 'no', 'run'])
    assert result.status == 'partial'
    assert result.data['settings']['max_iterations'] == 8
    assert result.data['seed_count'] == 1
    assert result.data['bond_paths'] == []
    assert result.data['search_complete'] is False
