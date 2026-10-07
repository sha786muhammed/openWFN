from pathlib import Path

from openwfn.assistant import AssistantSession
from openwfn.assistant_conversation import ConversationSession

SOURCE = Path(__file__).resolve().parents[2] / 'src/openwfn/example_data/everyday-qc/ethanol.molden'


def test_transcript_requests_complete_without_model_and_preserve_evidence():
    session = ConversationSession(file_session=AssistantSession(SOURCE))
    homo = session.ask('what is the humo value').record
    assert homo.status == 'success'
    assert homo.data['overall_homo_hartree'] == -0.331537655
    assert homo.provenance['input_sha256'] == '5dea76d46b2fd6a0cf6c264b5ffb65e67dfb2354d6dd4844780d252dcdab6276'
    pending = session.ask('atomic charges')
    assert pending.record is None
    charges = session.ask('Löwdin').record
    assert charges.analysis_name == 'lowdin'
    assert charges.data['electron_count'] == 26.0
    ir = session.ask('where the ir spectra')
    assert ir.record.status == 'failed'
    assert ir.record.analysis_name == 'ir-spectrum'
    assert 'frequency-job' in ir.text
    assert session.file_session.pending_request is None
    lumo = session.ask('show the LUMO value for this file').record
    assert lumo.data['alpha']['lumo_hartree'] == 0.5497350542
