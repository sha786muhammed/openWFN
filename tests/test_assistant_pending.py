from pathlib import Path

from openwfn.assistant import AnalysisPlan, AssistantSession

SOURCE = Path(__file__).resolve().parents[1] / 'src/openwfn/example_data/everyday-qc/ethanol.molden'


def test_new_clarification_after_success_retains_its_own_question():
    session = AssistantSession(SOURCE)
    session.ask('charge?', None)
    class Planner:
        def plan(self, question, context):
            if question == 'alpha':
                assert context['previous_question'] == 'Inspect alpha frontier orbitals please'
                return AnalysisPlan('analysis', 'frontier', {'spin': 'alpha'})
            return AnalysisPlan('clarify', clarification='spin')
    first = session.ask('Inspect alpha frontier orbitals please', Planner())
    assert first.record is None
    answer = session.ask('alpha', Planner())
    assert answer.record.status == 'success'
    assert session.pending_request is None


def test_population_followup_completes_without_model():
    session = AssistantSession(SOURCE)
    first = session.ask('atomic charges', None)
    assert first.record is None
    assert 'Mulliken' in first.text
    answer = session.ask('Löwdin', None)
    assert answer.record.analysis_name == 'lowdin'
    assert answer.record.status == 'success'


def test_explicit_new_request_cancels_old_pending_task():
    session = AssistantSession(SOURCE)
    session.ask('atomic charges', None)
    answer = session.ask('homo', None)
    assert answer.record.analysis_name == 'frontier-all'
    assert session.pending_request is None


def test_invalid_reply_keeps_task_and_bounds_clarifications():
    session = AssistantSession(SOURCE)
    session.ask('atomic charges', None)
    answer = session.ask('banana', None)
    assert answer.record is None
    assert 'Mulliken' in answer.text
    answer = session.ask('banana again', None)
    assert answer.record is None
    assert 'guided' in answer.text.lower()
    assert session.pending_request is None


def test_ambiguous_density_asks_operation_without_inference():
    session = AssistantSession(SOURCE)
    answer = session.ask('what is the total density', None)
    assert answer.record is None
    assert 'integrat' in answer.text.lower()
    assert 'cube' in answer.text.lower()
    assert session.pending_request is not None


def test_plain_projection_reply_does_not_become_population_request():
    class Planner:
        def plan(self, question, context):
            if question == 'lowdin':
                return AnalysisPlan('analysis', 'orbital-composition', {'mo': 'homo', 'method': 'lowdin'})
            return AnalysisPlan('clarify', clarification='projection-method')
    session = AssistantSession(SOURCE)
    session.ask('Which atoms contribute to HOMO?', Planner())
    answer = session.ask('lowdin', Planner())
    assert answer.record.analysis_name == 'orbital-composition'


def test_unrelated_new_question_does_not_inherit_pending_method():
    class Planner:
        def plan(self, question, context):
            assert context['previous_question'] is None
            return AnalysisPlan('analysis', 'frontier-all')
    session = AssistantSession(SOURCE)
    session.ask('atomic charges', None)
    answer = session.ask('Please inspect frontier energies for this molecule', Planner())
    assert answer.record.analysis_name == 'frontier-all'


def test_disconnect_clears_pending_but_keeps_evidence():
    from openwfn.assistant_conversation import ConversationSession
    controller = ConversationSession(file_session=AssistantSession(SOURCE))
    record = controller.ask('charge').record
    controller.ask('atomic charges')
    controller.disconnect()
    assert controller.file_session.pending_request is None
    assert controller.last_record is record


def test_changed_file_invalidates_pending_reply(tmp_path):
    import shutil
    path = tmp_path / 'ethanol.molden'
    shutil.copyfile(SOURCE, path)
    session = AssistantSession(path)
    session.ask('atomic charges', None)
    path.write_text(path.read_text() + '\n')
    session.refresh()
    assert session.pending_request is None


def test_explicit_points_must_survive_model_plan():
    import pytest
    class Planner:
        def plan(self, question, context):
            if question == '1, 2, 3':
                return AnalysisPlan('analysis', 'elf', {'x_bohr': 0., 'y_bohr': 0., 'z_bohr': 0.})
            return AnalysisPlan('clarify', clarification='points')
    session = AssistantSession(SOURCE)
    session.ask('Inspect ELF for my molecule', Planner())
    with pytest.raises(ValueError, match='selected point'):
        session.ask('1, 2, 3', Planner())
