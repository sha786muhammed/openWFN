from __future__ import annotations

import pytest

from openwfn.analysis.nto import select_nto_amplitude_block
from openwfn.errors import DataUnavailableError
from openwfn.parsers.excited.gaussian import parse_gaussian_excited_states
from openwfn.parsers.excited.orca import parse_orca_excited_states
from openwfn.parsers.excited.qchem import parse_qchem_excited_states


def test_gaussian_printed_transition_coefficients_remain_contributions_not_nto_matrix() -> None:
    parsed = parse_gaussian_excited_states(
        """
 #p CIS(NStates=1)/STO-3G
 Charge = 0 Multiplicity = 1
 Excited State   1:   Singlet-A      4.0000 eV  310.0 nm  f=0.1000
      1 -> 2        0.70710
 Normal termination of Gaussian
"""
    )
    assert parsed is not None
    state = parsed.jobs[0].states[0]
    assert len(state.contributions) == 1
    assert state.amplitudes == ()
    with pytest.raises(DataUnavailableError, match="complete explicitly supported"):
        select_nto_amplitude_block(state)


def test_orca_default_state_output_does_not_invent_dense_nto_matrix() -> None:
    parsed = parse_orca_excited_states(
        """
! CIS STO-3G
Total Charge       : 0
Multiplicity       : 1
STATE 1: E= 0.1470 au      4.0000 eV
ORCA TERMINATED NORMALLY
"""
    )
    assert parsed is not None
    state = parsed.jobs[0].states[0]
    assert state.amplitudes == ()
    with pytest.raises(DataUnavailableError, match="complete explicitly supported"):
        select_nto_amplitude_block(state)


def test_qchem_default_excited_state_output_does_not_invent_dense_nto_matrix() -> None:
    parsed = parse_qchem_excited_states(
        """
Q-Chem 6.3
$rem
METHOD CIS
$end
Charge = 0 Multiplicity = 1
Excited state 1: excitation energy (eV) = 4.0000
Multiplicity: Singlet
Oscillator Strength: 0.1000
Thank you very much for using Q-Chem
"""
    )
    assert parsed is not None
    state = parsed.jobs[0].states[0]
    assert state.amplitudes == ()
    with pytest.raises(DataUnavailableError, match="complete explicitly supported"):
        select_nto_amplitude_block(state)
