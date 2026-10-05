from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from openwfn.analysis import grids
from openwfn.ingest import load_input
from openwfn.model import Atom, CalculationMetadata, Molecule
from openwfn.output_properties import _normalize_output
from openwfn.parsers.gaussian.fchk import parse_fchk
from openwfn.vibrational import get_vibrational_record


def _single_atom_molecule() -> Molecule:
    return Molecule(
        (Atom(1, (0.0, 0.0, 0.0), nuclear_charge=1.0),),
        0,
        1,
        CalculationMetadata("fixture"),
    )


def test_grid_default_ceiling_can_be_explicitly_overridden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(grids, "MAX_GRID_POINTS", 10)
    molecule = _single_atom_molecule()

    with pytest.raises(ValueError, match="10"):
        grids.molecular_grid_points(molecule, spacing_bohr=1.0, padding_bohr=1.0)

    points, _origin, shape = grids.molecular_grid_points(
        molecule,
        spacing_bohr=1.0,
        padding_bohr=1.0,
        max_grid_points=27,
    )

    assert shape == (3, 3, 3)
    assert points.shape == (27, 3)


def test_fchk_vibrational_arrays_are_promoted_to_typed_record(tmp_path: Path) -> None:
    source = tmp_path / "h2_freq.fchk"
    source.write_text(
        "H2 frequency fixture\n"
        "SP        RHF        STO-3G\n"
        "Number of atoms I 2\n"
        "Atomic numbers I N= 2\n"
        " 1 1\n"
        "Nuclear charges R N= 2\n"
        " 1.00000000E+00 1.00000000E+00\n"
        "Current cartesian coordinates R N= 6\n"
        " 0.00000000E+00 0.00000000E+00 -7.00000000E-01\n"
        " 0.00000000E+00 0.00000000E+00  7.00000000E-01\n"
        "Charge I 0\n"
        "Multiplicity I 1\n"
        "Number of Normal Modes I 1\n"
        "Vib-E2 R N= 14\n"
        " 1.00000000E+03 1.50000000E+00 2.50000000E+00 3.50000000E+00 4.50000000E+00\n"
        " 1.00000000E-01 2.00000000E-01 0.00000000E+00 0.00000000E+00 0.00000000E+00\n"
        " 0.00000000E+00 0.00000000E+00 0.00000000E+00 0.00000000E+00\n"
        "Vib-Modes R N= 6\n"
        " 1.00000000E-01 0.00000000E+00 0.00000000E+00 -1.00000000E-01 0.00000000E+00 0.00000000E+00\n"
        "Vib-AtMass R N= 2\n"
        " 1.00782503E+00 1.00782503E+00\n",
        encoding="utf-8",
    )

    record = get_vibrational_record(parse_fchk(source))
    mode = record.modes[0]

    assert mode.frequency_cm1 == pytest.approx(1000.0)
    assert mode.reduced_mass_amu == pytest.approx(1.5)
    assert mode.force_constant_mdyne_per_angstrom == pytest.approx(2.5)
    assert mode.ir_intensity_km_mol == pytest.approx(3.5)
    assert mode.raman_activity_a4_amu == pytest.approx(4.5)
    assert mode.displacements == ((0.1, 0.0, 0.0), (-0.1, 0.0, 0.0))


def test_cclib_vibrations_can_be_normalized_for_registered_analyses() -> None:
    import openwfn.vibrational as vibrational

    converter = getattr(vibrational, "vibrational_record_from_cclib", None)
    assert converter is not None
    parsed = SimpleNamespace(
        metadata={"package": "ORCA", "package_version": "5.0"},
        vibfreqs=np.array([100.0, 250.0]),
        vibirs=np.array([4.0, 8.0]),
        vibrmasses=np.array([1.2, 1.4]),
        vibfconsts=np.array([0.3, 0.5]),
        vibramans=np.array([2.0, 3.0]),
        vibsyms=["A1", "B2"],
        vibdisps=np.array(
            [
                [[0.1, 0.0, 0.0], [-0.1, 0.0, 0.0]],
                [[0.0, 0.2, 0.0], [0.0, -0.2, 0.0]],
            ]
        ),
    )

    record = converter(parsed)

    assert record is not None
    assert [mode.frequency_cm1 for mode in record.modes] == [100.0, 250.0]
    assert [mode.ir_intensity_km_mol for mode in record.modes] == [4.0, 8.0]
    assert record.modes[1].symmetry == "B2"
    assert record.displacements_available is True


def test_properties_preserve_cclib_vibrational_and_thermochemistry_fields() -> None:
    parsed = SimpleNamespace(
        metadata={"package": "Gaussian", "package_version": "16", "success": True},
        natom=1,
        charge=0,
        mult=1,
        atomnos=np.array([1]),
        atomcoords=np.array([[[0.0, 0.0, 0.0]]]),
        scfenergies=np.array([-27.21138505]),
        homos=np.array([0]),
        moenergies=[np.array([-1.0])],
        atomcharges={},
        vibfreqs=np.array([1806.46, 3908.95, 3995.0]),
        vibirs=np.array([10.0, 20.0, 30.0]),
        enthalpy=-75.9,
        entropy=0.00025,
        freeenergy=-75.97,
        zpve=0.021,
    )

    data, _warnings = _normalize_output(parsed)

    assert data["vibfreqs"] == [1806.46, 3908.95, 3995.0]
    assert data["vibirs"] == [10.0, 20.0, 30.0]
    assert data["enthalpy"] == pytest.approx(-75.9)
    assert data["entropy"] == pytest.approx(0.00025)
    assert data["freeenergy"] == pytest.approx(-75.97)
    assert data["zpve"] == pytest.approx(0.021)


def test_molden_input_standard_psi4_filename_is_detected_by_header(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "h2o.molden.input"
    source.write_text("[Molden Format]\n[Atoms] AU\n", encoding="utf-8")
    sentinel = object()

    monkeypatch.setattr("openwfn.ingest._load_iodata", lambda path, *, format_id: sentinel)

    assert load_input(source) is sentinel
