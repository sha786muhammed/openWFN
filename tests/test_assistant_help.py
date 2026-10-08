from pathlib import Path

from openwfn.assistant import AssistantSession
from openwfn.assistant_conversation import ConversationSession

SOURCE = Path(__file__).resolve().parents[1] / 'src/openwfn/example_data/everyday-qc/ethanol.molden'


def test_fchk_guidance_does_not_invent_format_or_request_model():
    answer = ConversationSession().ask('explain about the .fchk')
    assert answer.record is None
    assert 'formchk' in answer.text
    assert '%fchk' not in answer.text and '$Molecule' not in answer.text
    assert 'formatted checkpoint' in answer.text.lower()


def test_missing_ir_guidance_keeps_file_and_names_required_records():
    controller = ConversationSession(file_session=AssistantSession(SOURCE))
    answer = controller.ask('where the ir spectra')
    assert answer.record.status == 'failed'
    assert 'frequenc' in answer.text.lower()
    assert 'intensit' in answer.text.lower()
    assert 'frequency' in answer.text.lower() and 'output' in answer.text.lower()
    assert controller.file_session.source == SOURCE.resolve()


def test_local_greeting_explains_no_model_onboarding():
    answer = ConversationSession().ask('hi')
    assert '/open' in answer.text and '/connect' in answer.text


def test_rendered_terminal_ir_failure_keeps_actionable_guidance():
    from openwfn.assistant_display import render_chat_answer
    answer = ConversationSession(file_session=AssistantSession(SOURCE)).ask('where the ir spectra')
    text = render_chat_answer(answer, question='where the ir spectra', source_label='ethanol.molden')
    assert 'frequency-job output' in text
    assert 'IR intensities' in text
