from __future__ import annotations

import numpy as np
import pytest

from openwfn.analysis.basis import evaluate_ao, overlap_matrix
from openwfn.analysis.grids import molecular_grid_points
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


def _calculation() -> CalculationData:
    molecule = Molecule(
        atoms=(Atom(1, (0.0, 0.0, 0.0)), Atom(1, (1.4, 0.0, 0.0))),
        charge=0,
        multiplicity=1,
        metadata=CalculationMetadata("SyntheticQC"),
    )
    basis = BasisSet(
        (
            BasisShell(0, 0, (1.0,), (1.0,)),
            BasisShell(1, 0, (0.8,), (1.0,)),
        )
    )
    overlap = overlap_matrix(basis, molecule)
    eigenvalues, eigenvectors = np.linalg.eigh(overlap)
    coefficients = eigenvectors @ np.diag(eigenvalues ** -0.5) @ eigenvectors.T
    orbitals = MolecularOrbitals(
        energies=(-0.6, 0.3),
        coefficients=tuple(tuple(float(value) for value in row) for row in coefficients),
        occupations=(2.0, 0.0),
        spin="restricted",
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
                        energy_ev=4.0,
                        amplitudes=(
                            AmplitudeBlock(
                                convention="cis-transition-amplitude-matrix",
                                values=(1.0,),
                                dimensions=(1, 1),
                            ),
                        ),
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


def test_selected_hole_field_matches_direct_ao_contraction_exactly() -> None:
    from openwfn.analysis.nto import map_nto_to_ao, nto_pair_field, select_nto_amplitude_block

    data = _calculation()
    state = data.records["excited_states"].jobs[0].states[0]
    block = select_nto_amplitude_block(state)
    mapped = map_nto_to_ao(data, block)
    spacing = 0.6
    padding = 1.2

    field = nto_pair_field(
        data,
        state=1,
        pair=1,
        component="hole",
        spacing_bohr=spacing,
        padding_bohr=padding,
        chunk_size=3,
    )
    points, _, _ = molecular_grid_points(
        data.molecule,
        spacing_bohr=spacing,
        padding_bohr=padding,
    )
    expected = evaluate_ao(data.basis, data.molecule, points) @ mapped.hole_coefficients[:, 0]

    np.testing.assert_allclose(np.asarray(field.grid.values), expected, atol=1e-13)
    np.testing.assert_allclose(field.ao_coefficients, mapped.hole_coefficients[:, 0], atol=1e-13)
    assert field.grid.value_unit == "bohr^-3/2"
    assert field.component == "hole"
    assert field.job == 1
    assert field.state == 1
    assert field.source_state == "S1"
    assert field.pair == 1
    assert field.spin_block == "restricted"
    assert field.amplitude_convention == "cis-transition-amplitude-matrix"
    assert field.weight == pytest.approx(1.0)
    assert field.ao_metric_norm == pytest.approx(1.0, abs=1e-12)


def test_selected_electron_field_matches_direct_ao_contraction_exactly() -> None:
    from openwfn.analysis.nto import map_nto_to_ao, nto_pair_field, select_nto_amplitude_block

    data = _calculation()
    state = data.records["excited_states"].jobs[0].states[0]
    mapped = map_nto_to_ao(data, select_nto_amplitude_block(state))
    spacing = 0.7
    padding = 1.0

    field = nto_pair_field(
        data,
        state=1,
        pair=1,
        component="electron",
        spacing_bohr=spacing,
        padding_bohr=padding,
        chunk_size=2,
    )
    points, _, _ = molecular_grid_points(
        data.molecule,
        spacing_bohr=spacing,
        padding_bohr=padding,
    )
    expected = evaluate_ao(data.basis, data.molecule, points) @ mapped.electron_coefficients[:, 0]

    np.testing.assert_allclose(np.asarray(field.grid.values), expected, atol=1e-13)
    np.testing.assert_allclose(field.ao_coefficients, mapped.electron_coefficients[:, 0], atol=1e-13)
    assert field.component == "electron"
    assert field.ao_metric_norm == pytest.approx(1.0, abs=1e-12)


def test_nto_field_chunking_is_numerically_equivalent() -> None:
    from openwfn.analysis.nto import nto_pair_field

    data = _calculation()
    first = nto_pair_field(
        data,
        state=1,
        pair=1,
        component="hole",
        spacing_bohr=0.8,
        padding_bohr=1.0,
        chunk_size=1,
    )
    second = nto_pair_field(
        data,
        state=1,
        pair=1,
        component="hole",
        spacing_bohr=0.8,
        padding_bohr=1.0,
        chunk_size=100,
    )
    np.testing.assert_allclose(first.grid.values, second.grid.values, atol=1e-14)


@pytest.mark.parametrize("pair", [0, 2, True])
def test_nto_field_uses_one_based_pair_selection(pair) -> None:
    from openwfn.analysis.nto import nto_pair_field

    with pytest.raises(ValueError, match="pair.*one-based"):
        nto_pair_field(
            _calculation(),
            state=1,
            pair=pair,
            component="hole",
            spacing_bohr=0.8,
            padding_bohr=1.0,
        )


def test_nto_field_rejects_unknown_component() -> None:
    from openwfn.analysis.nto import nto_pair_field

    with pytest.raises(ValueError, match="component.*hole.*electron"):
        nto_pair_field(
            _calculation(),
            state=1,
            pair=1,
            component="density",
            spacing_bohr=0.8,
            padding_bohr=1.0,
        )


def test_nto_field_reuses_existing_grid_safety_ceiling() -> None:
    from openwfn.analysis.nto import nto_pair_field

    with pytest.raises(ValueError, match="configured safety limit"):
        nto_pair_field(
            _calculation(),
            state=1,
            pair=1,
            component="hole",
            spacing_bohr=0.005,
            padding_bohr=2.0,
        )


def test_nto_cube_export_reuses_signed_amplitude_unit_and_provenance(tmp_path) -> None:
    from openwfn.analysis.nto import nto_cube_export

    output = tmp_path / "s1-hole-1.cube"
    result = nto_cube_export(
        _calculation(),
        state=1,
        pair=1,
        component="hole",
        spacing_bohr=0.7,
        padding_bohr=1.0,
        output_path=output,
        overwrite=False,
    )

    assert output.is_file()
    assert result.kind == "nto_cube"
    assert result.data["job"] == 1
    assert result.data["state"] == 1
    assert result.data["pair"] == 1
    assert result.data["component"] == "hole"
    assert result.data["spin_block"] == "restricted"
    assert result.data["amplitude_convention"] == "cis-transition-amplitude-matrix"
    assert result.units["amplitude"] == "bohr^-3/2"
    assert "component=hole" in output.read_text(encoding="utf-8").splitlines()[1]
    with pytest.raises(FileExistsError):
        nto_cube_export(
            _calculation(),
            state=1,
            pair=1,
            component="hole",
            spacing_bohr=0.7,
            padding_bohr=1.0,
            output_path=output,
            overwrite=False,
        )
