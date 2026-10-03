from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from openwfn.analysis.atom_quadrature import AtomQuadratureSettings
from openwfn.analysis.hirshfeld import HirshfeldSettings, hirshfeld_population
from openwfn.errors import DataUnavailableError, ValidationError
from openwfn.ingest import load_input
from openwfn.model import BasisSet, DensityMatrix

ROOT = Path(__file__).resolve().parents[1]


def _calculation(relative_path: str):
    normalized = load_input(ROOT / relative_path)
    assert normalized.calculation is not None
    return normalized.calculation


def test_hirshfeld_water_preserves_population_and_charge_closure_diagnostics() -> None:
    data = _calculation("examples/water/water.fchk")
    result = hirshfeld_population(data)

    assert result.method == "Hirshfeld"
    assert result.validation_status == "Experimental"
    assert len(result.atoms) == 3
    assert sum(atom.electron_population for atom in result.atoms) == pytest.approx(
        result.diagnostics.population_sum, abs=1.0e-10
    )
    assert sum(atom.net_charge for atom in result.atoms) == pytest.approx(
        result.diagnostics.integrated_charge, abs=1.0e-10
    )
    assert result.diagnostics.expected_electrons == pytest.approx(10.0)
    assert result.diagnostics.expected_molecular_charge == pytest.approx(0.0)
    assert result.diagnostics.population_partition_residual <= 1.0e-8
    assert result.diagnostics.electron_count_residual <= 5.0e-3
    assert result.diagnostics.charge_closure_residual <= 5.0e-3
    assert result.result_status == "success"


def test_hirshfeld_translation_invariance() -> None:
    data = _calculation("examples/water/water.fchk")
    shifted_atoms = tuple(
        replace(
            atom,
            coordinates=(
                atom.coordinates[0] + 3.25,
                atom.coordinates[1] - 1.75,
                atom.coordinates[2] + 0.5,
            ),
        )
        for atom in data.molecule.atoms
    )
    shifted = replace(data, molecule=replace(data.molecule, atoms=shifted_atoms))

    original_result = hirshfeld_population(data)
    shifted_result = hirshfeld_population(shifted)

    assert [atom.net_charge for atom in shifted_result.atoms] == pytest.approx(
        [atom.net_charge for atom in original_result.atoms], abs=2.0e-7
    )


def test_hirshfeld_unrestricted_analysis_uses_total_density_not_spin_density() -> None:
    data = _calculation("examples/everyday-qc/oxygen_triplet.molden")
    assert data.total_density is not None
    total = np.asarray(data.total_density.values, dtype=float)
    arbitrary_spin = DensityMatrix(
        values=tuple(tuple(float(value) for value in row) for row in np.eye(total.shape[0])),
        kind="spin",
        source="test-only spin perturbation",
    )

    baseline = hirshfeld_population(data)
    perturbed = hirshfeld_population(replace(data, spin_density=arbitrary_spin))

    assert baseline.diagnostics.expected_electrons == pytest.approx(16.0)
    assert [atom.net_charge for atom in perturbed.atoms] == pytest.approx(
        [atom.net_charge for atom in baseline.atoms], abs=1.0e-12
    )


def test_hirshfeld_does_not_renormalize_failed_coarse_grid_to_molecular_charge() -> None:
    data = _calculation("examples/water/water.fchk")
    settings = HirshfeldSettings(
        quadrature=AtomQuadratureSettings(
            radial_points=8,
            theta_points=4,
            phi_points=8,
            radial_extent_bohr=0.5,
            chunk_size=512,
        )
    )

    result = hirshfeld_population(data, settings=settings)

    direct_charge_sum = sum(atom.effective_nuclear_charge - atom.electron_population for atom in result.atoms)
    assert result.diagnostics.integrated_charge == pytest.approx(direct_charge_sum, abs=1.0e-12)
    assert result.diagnostics.charge_closure_residual > 0.1
    assert result.diagnostics.integrated_charge != pytest.approx(data.molecule.charge, abs=0.1)
    assert result.result_status == "partial"


def test_hirshfeld_requires_basis_and_total_density() -> None:
    data = _calculation("examples/water/water.fchk")

    with pytest.raises(DataUnavailableError, match="basis"):
        hirshfeld_population(replace(data, basis=None))
    with pytest.raises(DataUnavailableError, match="total density"):
        hirshfeld_population(replace(data, total_density=None))


def test_hirshfeld_rejects_unsupported_elements_without_fallback() -> None:
    data = _calculation("examples/water/water.fchk")
    atoms = list(data.molecule.atoms)
    atoms[0] = replace(atoms[0], atomic_number=9, nuclear_charge=None)
    unsupported = replace(data, molecule=replace(data.molecule, atoms=tuple(atoms)))

    with pytest.raises(ValidationError, match="Unsupported Hirshfeld reference element"):
        hirshfeld_population(unsupported)


def test_hirshfeld_rejects_ghost_ecp_and_effective_charge_ambiguity() -> None:
    data = _calculation("examples/water/water.fchk")
    assert data.basis is not None

    ghost_atoms = list(data.molecule.atoms)
    ghost_atoms[1] = replace(ghost_atoms[1], nuclear_charge=0.0)
    ghost = replace(data, molecule=replace(data.molecule, atoms=tuple(ghost_atoms)))
    with pytest.raises(ValidationError, match="ghost"):
        hirshfeld_population(ghost)

    ecp_basis = BasisSet(
        shells=data.basis.shells,
        name=data.basis.name,
        ecp_metadata=(("O", "test ECP"),),
    )
    with pytest.raises(ValidationError, match="ECP"):
        hirshfeld_population(replace(data, basis=ecp_basis))

    mismatch_atoms = list(data.molecule.atoms)
    mismatch_atoms[0] = replace(mismatch_atoms[0], nuclear_charge=6.0)
    mismatch = replace(data, molecule=replace(data.molecule, atoms=tuple(mismatch_atoms)))
    with pytest.raises(ValidationError, match="effective nuclear charge"):
        hirshfeld_population(mismatch)
