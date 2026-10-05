from __future__ import annotations

import numpy as np
import pytest

from openwfn.analysis.basis import overlap_matrix
from openwfn.analysis.registry import available_analyses, run_analysis
from openwfn.errors import DataUnavailableError
from openwfn.excited_states import (
    AmplitudeBlock,
    ExcitedState,
    ExcitedStateCollection,
    ExcitedStateJob,
)
from openwfn.model import (
    Atom,
    BasisSet,
    BasisShell,
    CalculationData,
    CalculationMetadata,
    MolecularOrbitals,
    Molecule,
)


def _calculation(*, amplitudes: tuple[AmplitudeBlock, ...] | None = None) -> CalculationData:
    molecule = Molecule(
        atoms=tuple(Atom(1, (3.0 * index, 0.0, 0.0)) for index in range(4)),
        charge=0,
        multiplicity=1,
        metadata=CalculationMetadata("SyntheticQC"),
    )
    basis = BasisSet(tuple(BasisShell(index, 0, (1.0,), (1.0,)) for index in range(4)))
    overlap = overlap_matrix(basis, molecule)
    eigenvalues, eigenvectors = np.linalg.eigh(overlap)
    coefficients = eigenvectors @ np.diag(eigenvalues ** -0.5) @ eigenvectors.T
    orbitals = MolecularOrbitals(
        energies=(-0.9, -0.5, 0.2, 0.6),
        coefficients=tuple(tuple(float(value) for value in row) for row in coefficients),
        occupations=(2.0, 2.0, 0.0, 0.0),
        spin="restricted",
    )
    if amplitudes is None:
        amplitudes = (
            AmplitudeBlock(
                convention="cis-transition-amplitude-matrix",
                values=(0.8, 0.0, 0.0, 0.6),
                dimensions=(2, 2),
            ),
        )
    collection = ExcitedStateCollection(
        jobs=(
            ExcitedStateJob(
                index=1,
                source_program="SyntheticQC",
                method_family="cis",
                method_detail="CIS",
                reference_state="S0",
                states=(
                    ExcitedState(
                        index=1,
                        source_state="S1",
                        energy_ev=4.2,
                        oscillator_strength=0.15,
                        amplitudes=amplitudes,
                    ),
                ),
            ),
        )
    )
    return CalculationData(
        molecule=molecule,
        basis=basis,
        alpha_orbitals=orbitals,
        records={"excited_states": collection},
    )


def test_nto_is_registered_and_returns_bounded_renderer_independent_pair_table() -> None:
    data = _calculation()

    result = run_analysis(data, "nto", state=1)

    assert "nto" in available_analyses()
    assert result.kind == "natural_transition_orbitals"
    assert result.analysis_name == "nto"
    assert result.validation_status == "Experimental"
    assert result.data["job"] == 1
    assert result.data["state"] == 1
    assert result.data["source_state"] == "S1"
    assert result.data["source_program"] == "SyntheticQC"
    assert result.data["method_family"] == "cis"
    assert result.data["method_detail"] == "CIS"
    assert result.data["spin_block"] == "restricted"
    assert result.data["amplitude_convention"] == "cis-transition-amplitude-matrix"
    assert result.data["matrix_dimensions"] == [2, 2]
    assert result.data["occupied_mo_indices"] == [1, 2]
    assert result.data["virtual_mo_indices"] == [3, 4]
    assert result.data["pair_count_total"] == 2
    assert result.data["pair_count_returned"] == 2
    assert result.data["omitted_pair_count"] == 0
    assert [row["pair"] for row in result.data["pairs"]] == [1, 2]
    assert [row["weight"] for row in result.data["pairs"]] == pytest.approx([0.64, 0.36])
    assert result.data["pairs"][-1]["cumulative_weight"] == pytest.approx(1.0)
    assert max(row["hole_norm_residual"] for row in result.data["pairs"]) < 1e-10
    assert max(row["electron_norm_residual"] for row in result.data["pairs"]) < 1e-10
    assert result.units["weight"] == "dimensionless"
    assert result.units["ao_overlap_norm"] == "dimensionless"


def test_nto_pair_filtering_tracks_weight_and_limit_omissions() -> None:
    result = run_analysis(_calculation(), "nto", state=1, max_pairs=1, min_weight=0.4)

    assert result.data["pair_count_total"] == 2
    assert result.data["pair_count_returned"] == 1
    assert result.data["omitted_by_weight"] == 1
    assert result.data["omitted_by_limit"] == 0
    assert result.data["omitted_pair_count"] == 1
    assert result.data["pairs"][0]["pair"] == 1


def test_nto_limit_can_omit_pairs_after_weight_filtering() -> None:
    result = run_analysis(_calculation(), "nto", state=1, max_pairs=1, min_weight=0.0)

    assert result.data["omitted_by_weight"] == 0
    assert result.data["omitted_by_limit"] == 1
    assert result.data["omitted_pair_count"] == 1


@pytest.mark.parametrize("state", [0, 2, True])
def test_nto_requires_valid_one_based_state(state) -> None:
    with pytest.raises(ValueError, match="state.*one-based"):
        run_analysis(_calculation(), "nto", state=state)


@pytest.mark.parametrize("job", [0, 2, True])
def test_nto_requires_valid_one_based_job(job) -> None:
    with pytest.raises(ValueError, match="job.*one-based"):
        run_analysis(_calculation(), "nto", state=1, job=job)


@pytest.mark.parametrize("max_pairs", [0, -1, True, 1001])
def test_nto_rejects_invalid_or_overlarge_pair_limit(max_pairs) -> None:
    with pytest.raises(ValueError, match="max_pairs"):
        run_analysis(_calculation(), "nto", state=1, max_pairs=max_pairs)


@pytest.mark.parametrize("min_weight", [-0.1, 1.1, float("nan"), float("inf")])
def test_nto_rejects_invalid_min_weight(min_weight: float) -> None:
    with pytest.raises(ValueError, match="min_weight"):
        run_analysis(_calculation(), "nto", state=1, min_weight=min_weight)


def test_nto_refuses_truncated_or_unsupported_amplitudes() -> None:
    truncated = AmplitudeBlock(
        convention="cis-transition-amplitude-matrix",
        values=(0.8, 0.1, -0.2),
        dimensions=(2, 2),
    )
    with pytest.raises(DataUnavailableError, match="NTO-ready transition amplitudes"):
        run_analysis(_calculation(amplitudes=(truncated,)), "nto", state=1)


def test_nto_refuses_ambiguous_spin_blocks_without_selector() -> None:
    alpha = AmplitudeBlock(
        convention="cis-transition-amplitude-matrix",
        values=(0.8, 0.0, 0.0, 0.6),
        dimensions=(2, 2),
        spin_block="alpha",
    )
    beta = AmplitudeBlock(
        convention="cis-transition-amplitude-matrix",
        values=(0.7, 0.0, 0.0, 0.5),
        dimensions=(2, 2),
        spin_block="beta",
    )
    with pytest.raises(DataUnavailableError, match="ambiguous"):
        run_analysis(_calculation(amplitudes=(alpha, beta)), "nto", state=1)


def test_nto_registry_signature_rejects_unapproved_parameters() -> None:
    with pytest.raises(TypeError):
        run_analysis(_calculation(), "nto", state=1, spacing_bohr=0.2)
