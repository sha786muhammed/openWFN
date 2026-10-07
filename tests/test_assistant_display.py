import importlib
import importlib.util

from openwfn.assistant import AssistantAnswer
from openwfn.results import ResultRecord


def display():
    assert importlib.util.find_spec('openwfn.assistant_display'), 'Compact chat display missing'
    return importlib.import_module('openwfn.assistant_display')


def test_homo_reply_selects_requested_value_preserving_warning():
    record = ResultRecord(kind='frontier_orbitals', analysis_name='frontier-all', analysis_version='1',
        data={'overall_homo_number': 13, 'overall_homo_hartree': -0.331537655,
              'reference_kind': 'restricted_closed_shell'}, warnings=('Example warning',),
        status='partial', validation_status='Experimental')
    text = display().render_chat_answer(AssistantAnswer('full record', record),
                                         question='What is my HOMO?', source_label='ethanol.molden')
    assert '-0.331537655' in text and 'Hartree' in text and '13' in text
    assert 'partial' in text and 'Experimental' in text and 'Example warning' in text
    assert 'ethanol.molden' in text and '/record' in text


def test_explanation_is_not_relabelled_as_calculated():
    answer = AssistantAnswer('Model explanation · No calculation was run\nConceptual answer.')
    assert display().render_chat_answer(answer, question='Explain', source_label=None) == answer.text


def test_model_text_cannot_execute_c1_terminal_controls():
    text = display().render_chat_answer(AssistantAnswer('\x1b[2J\x9b2JAnswer'), question='Explain', source_label=None)
    assert '\x1b' not in text and '\x9b' not in text


def test_gap_question_shows_gap_instead_of_only_homo():
    record = ResultRecord(kind='frontier_orbitals', analysis_name='frontier-all', analysis_version='1',
        data={'alpha': {'spin': 'restricted', 'gap_ev': 23.98065208},
              'overall_homo_number': 13, 'overall_homo_hartree': -0.331537655})
    text = display().render_chat_answer(AssistantAnswer('', record),
        question='What is the HOMO-LUMO gap?', source_label='ethanol.molden')
    assert '23.98065208 eV' in text
    assert 'not an optical' in text
