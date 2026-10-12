import pytest

from openwfn.assistant import AssistantAnswer
from openwfn.assistant_display import render_chat_answer
from openwfn.results import ResultRecord


@pytest.mark.parametrize('question', ['HOMO?', 'LUMO?', 'HOMO-LUMO gap?'])
def test_compact_frontier_answer_preserves_unknown_fchk_convergence(question):
    record = ResultRecord(kind='frontier_orbitals', analysis_name='frontier-all',
        data={'overall_homo_number': 35, 'overall_homo_hartree': -0.152537251,
              'alpha': {'spin': 'restricted', 'lumo_number': 36,
                        'lumo_hartree': 0.0369876459, 'gap_ev': 5.15723517}},
        provenance={'source_format': 'fchk', 'source_path': 'example.fchk'},
        warnings=('Preserved diagnostic',))
    text = render_chat_answer(AssistantAnswer('', record), question=question, source_label='example.fchk')
    assert 'convergence is not established' in text
    assert 'Preserved diagnostic' in text
    assert text.count('convergence is not established') == 1


def test_filename_does_not_establish_failed_source_convergence():
    record = ResultRecord(kind='frontier_orbitals', data={'overall_homo_number': 1,
        'overall_homo_hartree': -0.5}, provenance={'source_format': 'molden'})
    text = render_chat_answer(AssistantAnswer('', record), question='homo', source_label='unconverged.molden')
    assert 'failed' not in text
