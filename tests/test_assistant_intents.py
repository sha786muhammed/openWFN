from pathlib import Path

import pytest

from openwfn.assistant import AssistantSession, _direct_plan
from openwfn.assistant_conversation import ConversationSession

SOURCE = Path(__file__).resolve().parents[1] / 'src/openwfn/example_data/everyday-qc/ethanol.molden'


@pytest.mark.parametrize('question', [
    'what is the humo value', 'what is the Homo value of the .fchk',
    'What is my HOMO energy?', 'show the LUMO value for this file',
])
def test_common_frontier_wording_uses_engine_without_inference(question):
    plan = _direct_plan(question)
    assert plan is not None
    assert plan.analysis == 'frontier-all'
    answer = ConversationSession(file_session=AssistantSession(SOURCE)).ask(question)
    assert answer.record.status == 'success'
    assert answer.record.data['overall_homo_hartree'] == -0.331537655


@pytest.mark.parametrize('question,analysis', [
    ('where the ir spectra', 'ir-spectrum'),
    ('vibrational spectra', 'vibrations'),
    ('show the Raman spectrum', 'raman-spectrum'),
])
def test_missing_spectroscopy_has_local_capability_failure(question, analysis):
    answer = ConversationSession(file_session=AssistantSession(SOURCE)).ask(question)
    assert answer.record is not None
    assert answer.record.analysis_name == analysis
    assert answer.record.status == 'failed'
    assert 'unavailable' in answer.text.lower()


@pytest.mark.parametrize('question', ['HOMO-1', 'HOMO − 1 energy', 'total density',
                                      'spin density', 'compare HOMO energy with water'])
def test_ambiguous_or_distinct_requests_are_not_frontier_guesses(question):
    assert _direct_plan(question) is None


def test_frequency_output_ir_uses_spectrum_not_generic_output_properties():
    source = Path(__file__).resolve().parent / 'fixtures/gaussian/vibrations/water_freq.log'
    answer = ConversationSession(file_session=AssistantSession(source)).ask('where the ir spectra')
    assert answer.record.analysis_name == 'ir-spectrum'
    assert answer.record.status == 'success'
    assert answer.record.validation_status == 'Experimental'
