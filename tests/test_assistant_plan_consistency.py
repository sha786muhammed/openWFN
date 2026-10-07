from pathlib import Path

import pytest

from openwfn.assistant import AnalysisPlan, AssistantSession

SOURCE = Path(__file__).resolve().parents[1] / 'src/openwfn/example_data/everyday-qc/ethanol.molden'


def test_ir_request_never_executes_population_from_model():
    class Planner:
        def plan(self, question, context):
            return AnalysisPlan('analysis', 'mulliken')
    session = AssistantSession(SOURCE)
    with pytest.raises(ValueError, match='requested'):
        session.ask('Please analyse the IR spectrum from this molecule', Planner())
    assert session.last_plan is None


@pytest.mark.parametrize('spin', ['restricted', 'ALPHA', 'banana', None])
def test_invalid_orbital_channel_is_rejected_before_engine(spin):
    with pytest.raises(ValueError, match='spin'):
        AnalysisPlan('analysis', 'frontier', {'spin': spin})


def test_explicit_clarification_spin_cannot_be_overridden():
    class Planner:
        def plan(self, question, context):
            if question == 'beta':
                return AnalysisPlan('analysis', 'frontier', {'spin': 'alpha'})
            return AnalysisPlan('clarify', clarification='spin')
    session = AssistantSession(SOURCE)
    session.ask('Inspect the channel frontier energies', Planner())
    with pytest.raises(ValueError, match='channel'):
        session.ask('beta', Planner())


def test_ir_request_cannot_start_a_population_clarification_loop():
    class Planner:
        def plan(self, question, context):
            return AnalysisPlan('clarify', clarification='method')
    with pytest.raises(ValueError, match='requested'):
        AssistantSession(SOURCE).ask('Please analyse IR intensities for this molecule', Planner())


def test_model_cannot_answer_offset_orbital_with_plain_frontier_record():
    class Planner:
        def plan(self, question, context):
            return AnalysisPlan('analysis', 'frontier-all')
    with pytest.raises(ValueError, match='offset'):
        AssistantSession(SOURCE).ask('What is HOMO-1 energy?', Planner())
