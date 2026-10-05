from __future__ import annotations

import numpy as np
import pytest

from openwfn.errors import DataUnavailableError
from openwfn.excited_states import AmplitudeBlock, ExcitedState


def test_complete_cis_matrix_is_nto_ready_and_reconstructs_row_major() -> None:
    from openwfn.analysis.nto import transition_matrix_from_block

    block = AmplitudeBlock(
        convention="cis-transition-amplitude-matrix",
        values=(0.8, 0.1, -0.2, 0.3, 0.05, -0.4),
        dimensions=(2, 3),
    )

    assert block.nto_ready
    np.testing.assert_allclose(
        transition_matrix_from_block(block),
        [[0.8, 0.1, -0.2], [0.3, 0.05, -0.4]],
    )


def test_complete_indexed_matrix_reconstructs_only_with_full_unique_coverage() -> None:
    from openwfn.analysis.nto import transition_matrix_from_block

    block = AmplitudeBlock(
        convention="cis-transition-amplitude-matrix",
        values=(0.4, 0.1, -0.2, 0.3),
        indices=((1, 1), (0, 1), (1, 0), (0, 0)),
        dimensions=(2, 2),
    )

    assert block.nto_ready
    np.testing.assert_allclose(transition_matrix_from_block(block), [[0.3, 0.1], [-0.2, 0.4]])


@pytest.mark.parametrize(
    "indices",
    [
        ((0, 0), (0, 1), (1, 0), (1, 0)),  # duplicate and therefore incomplete
        ((0, 0), (0, 1), (1, 0), (2, 0)),  # out of range
        ((0,), (0, 1), (1, 0), (1, 1)),  # wrong index rank
    ],
)
def test_indexed_matrix_rejects_duplicate_out_of_range_or_wrong_rank_entries(indices) -> None:
    block = AmplitudeBlock(
        convention="cis-transition-amplitude-matrix",
        values=(0.4, 0.1, -0.2, 0.3),
        indices=indices,
        dimensions=(2, 2),
    )
    assert not block.nto_ready


def test_truncated_dense_or_indexed_matrices_are_not_nto_ready() -> None:
    dense = AmplitudeBlock(
        convention="cis-transition-amplitude-matrix",
        values=(0.8, 0.1, -0.2),
        dimensions=(2, 2),
    )
    indexed = AmplitudeBlock(
        convention="cis-transition-amplitude-matrix",
        values=(0.8, 0.1, -0.2),
        indices=((0, 0), (0, 1), (1, 0)),
        dimensions=(2, 2),
    )

    assert not dense.nto_ready
    assert not indexed.nto_ready


def test_transition_density_requires_explicit_occupied_virtual_domains() -> None:
    implicit = AmplitudeBlock(
        convention="transition-density-matrix",
        values=(0.8, 0.1, -0.2, 0.3),
        dimensions=(2, 2),
    )
    explicit = AmplitudeBlock(
        convention="transition-density-matrix",
        values=(0.8, 0.1, -0.2, 0.3),
        dimensions=(2, 2),
        row_domain="occupied",
        column_domain="virtual",
    )
    reversed_domains = AmplitudeBlock(
        convention="transition-density-matrix",
        values=(0.8, 0.1, -0.2, 0.3),
        dimensions=(2, 2),
        row_domain="virtual",
        column_domain="occupied",
    )

    assert not implicit.nto_ready
    assert explicit.nto_ready
    assert not reversed_domains.nto_ready


@pytest.mark.parametrize(
    "convention",
    [
        "printed transition percentage",
        "eom-right-vector",
        "tddft-x-amplitudes",
        "tddft-y-amplitudes",
        "adc-isr-amplitudes",
        "configuration-coefficients",
        "mystery coefficients",
    ],
)
def test_unsupported_source_conventions_never_become_nto_ready(convention: str) -> None:
    block = AmplitudeBlock(
        convention=convention,
        values=(0.8, 0.1, -0.2, 0.3),
        dimensions=(2, 2),
    )
    assert not block.nto_ready


def test_multiple_spin_blocks_require_an_explicit_selector() -> None:
    from openwfn.analysis.nto import select_nto_amplitude_block

    alpha = AmplitudeBlock(
        convention="cis-transition-amplitude-matrix",
        values=(0.8, 0.1, -0.2, 0.3),
        dimensions=(2, 2),
        spin_block="alpha",
    )
    beta = AmplitudeBlock(
        convention="cis-transition-amplitude-matrix",
        values=(0.7, 0.2, -0.1, 0.4),
        dimensions=(2, 2),
        spin_block="beta",
    )
    state = ExcitedState(index=1, energy_ev=4.2, amplitudes=(alpha, beta))

    with pytest.raises(DataUnavailableError, match="ambiguous"):
        select_nto_amplitude_block(state)
    assert select_nto_amplitude_block(state, spin="alpha") is alpha
    assert select_nto_amplitude_block(state, spin="beta") is beta


def test_nto_selection_rejects_states_without_an_eligible_complete_matrix() -> None:
    from openwfn.analysis.nto import select_nto_amplitude_block

    truncated = AmplitudeBlock(
        convention="cis-transition-amplitude-matrix",
        values=(0.8, 0.1, -0.2),
        dimensions=(2, 2),
    )
    state = ExcitedState(index=1, energy_ev=4.2, amplitudes=(truncated,))

    with pytest.raises(DataUnavailableError, match="complete.*transition matrix"):
        select_nto_amplitude_block(state)
