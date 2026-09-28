from pathlib import Path

import numpy as np

from openwfn.analysis.electrostatics import nuclear_esp
from openwfn.constants import BOHR_TO_ANGSTROM
from openwfn.exporters.cube import format_cube
from openwfn.model import Atom, CalculationData, CalculationMetadata, Molecule, VolumetricGrid
from openwfn.services import molecular_summary


def _unit_grid() -> VolumetricGrid:
    step = BOHR_TO_ANGSTROM
    return VolumetricGrid(
        origin=(0.0, 0.0, 0.0),
        axes=((step, 0.0, 0.0), (0.0, step, 0.0), (0.0, 0.0, step)),
        shape=(1, 1, 1),
        values=(0.0,),
        value_unit="electron/bohr^3",
    )


def test_nuclear_esp_uses_effective_ecp_charge() -> None:
    molecule = Molecule(
        (Atom(14, (0.0, 0.0, 0.0), nuclear_charge=4.0),),
        0,
        1,
        CalculationMetadata("fixture"),
    )

    value = nuclear_esp(molecule, np.array(((1.0, 0.0, 0.0),)))[0]

    assert value == 4.0


def test_ghost_center_has_zero_nuclear_esp() -> None:
    molecule = Molecule(
        (Atom(8, (0.0, 0.0, 0.0), nuclear_charge=0.0),),
        0,
        1,
        CalculationMetadata("fixture"),
    )

    value = nuclear_esp(molecule, np.array(((1.0, 0.0, 0.0),)))[0]

    assert value == 0.0


def test_cube_header_keeps_element_identity_but_writes_effective_charge() -> None:
    molecule = Molecule(
        (Atom(14, (0.0, 0.0, 0.0), nuclear_charge=4.0),),
        0,
        1,
        CalculationMetadata("fixture"),
    )

    lines = format_cube(_unit_grid(), molecule).splitlines()
    atom_fields = lines[6].split()

    assert atom_fields[0] == "14"
    assert float(atom_fields[1]) == 4.0


def test_summary_excludes_ghost_from_physical_structure() -> None:
    molecule = Molecule(
        (
            Atom(1, (0.0, 0.0, 0.0), nuclear_charge=1.0),
            Atom(8, (0.7, 0.0, 0.0), nuclear_charge=0.0),
        ),
        0,
        2,
        CalculationMetadata("fixture"),
    )

    result = molecular_summary(CalculationData(molecule))

    assert result.data["centers"] == 2
    assert result.data["physical_nuclei"] == 1
    assert result.data["ghost_centers"] == 1
    assert result.data["atoms"] == 1
    assert result.data["formula"] == "H"
    assert result.data["center_of_mass"] == [0.0, 0.0, 0.0]
    assert result.data["bond_count"] == 0
    assert result.data["fragments"] == 1
    assert result.data["bond_source"] == "covalent-radius heuristic"
    assert any("ghost" in warning.lower() for warning in result.warnings)


def test_ordinary_summary_declares_inferred_bond_source() -> None:
    molecule = Molecule(
        (
            Atom(1, (0.0, 0.0, 0.0), nuclear_charge=1.0),
            Atom(1, (0.74, 0.0, 0.0), nuclear_charge=1.0),
        ),
        0,
        1,
        CalculationMetadata("fixture"),
    )

    result = molecular_summary(CalculationData(molecule))

    assert result.data["bond_source"] == "covalent-radius heuristic"
    assert result.data["centers"] == 2
    assert result.data["physical_nuclei"] == 2
    assert result.data["ghost_centers"] == 0
