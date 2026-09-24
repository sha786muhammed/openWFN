import json
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from scripts.capture_qc_iodata import build_reference, write_reference


def fake_data(*, energy: float = -1.25) -> SimpleNamespace:
    orbitals = SimpleNamespace(
        energiesa=np.array([-0.5, 0.2]),
        energiesb=np.array([-0.45, 0.25]),
        occsa=np.array([1.0, 0.0]),
        occsb=np.array([0.0, 0.0]),
        kind="unrestricted",
        spinpol=1.0,
    )
    return SimpleNamespace(
        energy=energy,
        charge=0.0,
        spinpol=1.0,
        atnums=np.array([3, 1]),
        atcoords=np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 3.0]]),
        mo=orbitals,
    )


def test_build_reference_is_deterministic_and_preserves_input_hash(tmp_path: Path) -> None:
    source = tmp_path / "sample.fchk"
    source.write_text("independent fixture\n", encoding="utf-8")

    payload = build_reference(source, lambda _: fake_data(), "1.0.1")

    assert payload == {
        "schema_version": "1.0",
        "program": "qc-iodata",
        "program_version": "1.0.1",
        "input_sha256": sha256(source.read_bytes()).hexdigest(),
        "energy_hartree": -1.25,
        "charge": 0,
        "multiplicity": 2,
        "atomic_numbers": [3, 1],
        "coordinates_bohr": [[0.0, 0.0, 0.0], [0.0, 0.0, 3.0]],
        "orbital_kind": "unrestricted",
        "alpha_orbital_energies_hartree": [-0.5, 0.2],
        "beta_orbital_energies_hartree": [-0.45, 0.25],
        "alpha_orbital_occupations": [1.0, 0.0],
        "beta_orbital_occupations": [0.0, 0.0],
    }

    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    write_reference(payload, first)
    write_reference(payload, second)
    assert first.read_bytes() == second.read_bytes()
    assert json.loads(first.read_text(encoding="utf-8")) == payload


def test_build_reference_rejects_non_finite_numbers(tmp_path: Path) -> None:
    source = tmp_path / "sample.fchk"
    source.write_text("fixture\n", encoding="utf-8")

    with pytest.raises(ValueError, match="finite"):
        build_reference(source, lambda _: fake_data(energy=float("nan")), "1.0.1")


def test_build_reference_normalizes_parser_errors(tmp_path: Path) -> None:
    source = tmp_path / "malformed.fchk"
    source.write_text("broken fixture\n", encoding="utf-8")

    def reject(_: str) -> SimpleNamespace:
        raise RuntimeError("adjacent fields")

    with pytest.raises(ValueError, match="qc-iodata could not parse.*adjacent fields"):
        build_reference(source, reject, "1.0.1")


def test_write_reference_protects_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "reference.json"
    output.write_text("keep\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="Output exists"):
        write_reference({"schema_version": "1.0"}, output)

    assert output.read_text(encoding="utf-8") == "keep\n"
