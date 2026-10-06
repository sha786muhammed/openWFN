from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_qtaim_basins_critic2.py"
FIXTURE = ROOT / "tests" / "fixtures" / "critic2" / "qtaim_integrals_sample.out"


def _module():
    assert SCRIPT.is_file(), "Critic2 basin validation parser has not been implemented"
    spec = importlib.util.spec_from_file_location("validate_qtaim_basins_critic2", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_critic2_basin_output_reads_positions_and_population() -> None:
    module = _module()
    rows = module.parse_critic2_basin_output(FIXTURE.read_text(encoding="utf-8"))

    assert [row.atomic_number for row in rows] == [8, 1, 1]
    assert [row.name for row in rows] == ["O", "H", "H"]
    assert [row.population for row in rows] == pytest.approx([8.4, 0.8, 0.8])
    np.testing.assert_allclose(
        np.asarray([row.position_bohr for row in rows]),
        np.asarray([[0.0, 0.0, 0.0], [1.43, 1.10, 0.0], [-1.43, 1.10, 0.0]]),
        rtol=0.0,
        atol=1.0e-12,
    )


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda text: text.replace(
                "  3    3    3       H   1  1    8.00000000E+00  8.00000000E-01 -5.00000000E-05",
                "",
            ),
            "missing|mismatch",
        ),
        (
            lambda text: text.replace(
                "  3    3    3       H   1  1    8.00000000E+00  8.00000000E-01 -5.00000000E-05",
                "  2    3    3       H   1  1    8.00000000E+00  8.00000000E-01 -5.00000000E-05",
            ),
            "duplicate",
        ),
        (
            lambda text: text.replace("8.40000000E+00", "NaN"),
            "finite|nonfinite",
        ),
    ],
)
def test_parse_critic2_basin_output_rejects_malformed_atomic_tables(mutator, message: str) -> None:
    module = _module()
    text = mutator(FIXTURE.read_text(encoding="utf-8"))

    with pytest.raises(ValueError, match=message):
        module.parse_critic2_basin_output(text)


def test_verify_fixture_sha256_rejects_mismatch(tmp_path: Path) -> None:
    module = _module()
    path = tmp_path / "fixture.fchk"
    path.write_text("fixture", encoding="utf-8")

    with pytest.raises(ValueError, match="SHA-256|sha256|hash"):
        module.verify_fixture_sha256(path, "0" * 64)


def test_map_critic2_rows_to_atoms_uses_element_and_geometry_not_table_order() -> None:
    module = _module()
    rows = module.parse_critic2_basin_output(FIXTURE.read_text(encoding="utf-8"))
    shuffled = [rows[2], rows[0], rows[1]]
    atomic_numbers = np.asarray([1, 8, 1])
    atom_positions_bohr = np.asarray(
        [[1.43, 1.10, 0.0], [0.0, 0.0, 0.0], [-1.43, 1.10, 0.0]],
        dtype=float,
    )

    ordered = module.map_critic2_rows_to_atoms(
        shuffled,
        atomic_numbers,
        atom_positions_bohr,
        tolerance_bohr=1.0e-6,
    )

    assert [row.population for row in ordered] == pytest.approx([0.8, 8.4, 0.8])
    assert [row.atomic_number for row in ordered] == [1, 8, 1]


def test_map_critic2_rows_to_atoms_rejects_ambiguous_or_missing_match() -> None:
    module = _module()
    rows = module.parse_critic2_basin_output(FIXTURE.read_text(encoding="utf-8"))

    with pytest.raises(ValueError, match="match|mapping"):
        module.map_critic2_rows_to_atoms(
            rows,
            np.asarray([8, 1, 1]),
            np.asarray([[0.0, 0.0, 0.0], [50.0, 0.0, 0.0], [-50.0, 0.0, 0.0]]),
            tolerance_bohr=0.1,
        )
