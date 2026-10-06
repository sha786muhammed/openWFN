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


def test_parse_critic2_basin_output_normalizes_critic2_ang_token_to_bohr() -> None:
    module = _module()
    text = FIXTURE.read_text(encoding="utf-8").replace("Position (bohr)", "Position (ang_)")
    rows = module.parse_critic2_basin_output(text)

    expected = np.asarray([[0.0, 0.0, 0.0], [1.43, 1.10, 0.0], [-1.43, 1.10, 0.0]])
    np.testing.assert_allclose(
        np.asarray([row.position_bohr for row in rows]),
        expected / module.BOHR_TO_ANGSTROM,
        rtol=0.0,
        atol=1.0e-12,
    )


def test_parse_critic2_molecular_rows_accept_nonapplicable_multiplicity() -> None:
    module = _module()
    text = FIXTURE.read_text(encoding="utf-8")
    text = text.replace("   8  1 ", "   8  -- ").replace("   1  1 ", "   1  -- ")

    rows = module.parse_critic2_basin_output(text)

    assert [row.atomic_number for row in rows] == [8, 1, 1]
    assert [row.multiplicity for row in rows] == [None, None, None]
    assert [row.population for row in rows] == pytest.approx([8.4, 0.8, 0.8])


def test_parse_critic2_molecular_properties_without_volume_column() -> None:
    module = _module()
    text = FIXTURE.read_text(encoding="utf-8")
    text = text.replace(
        "# Id   cp   ncp   Name  Z   mult     Volume            Pop             Lap",
        "# Id   cp   ncp   Name  Z   mult       Pop             Lap",
    )
    text = text.replace(
        "  1    1    1       O   8  1    1.20000000E+01  8.40000000E+00  1.00000000E-04",
        "  1    1    1       O   8  1    8.40000000E+00  1.00000000E-04",
    )
    text = text.replace(
        "  2    2    2       H   1  1    8.00000000E+00  8.00000000E-01 -5.00000000E-05",
        "  2    2    2       H   1  1    8.00000000E-01 -5.00000000E-05",
    )
    text = text.replace(
        "  3    3    3       H   1  1    8.00000000E+00  8.00000000E-01 -5.00000000E-05",
        "  3    3    3       H   1  1    8.00000000E-01 -5.00000000E-05",
    )
    text = text.replace(
        "  Sum                            2.80000000E+01  1.00000000E+01  0.00000000E+00",
        "  Sum                            1.00000000E+01  0.00000000E+00",
    )

    rows = module.parse_critic2_basin_output(text)

    assert [row.volume for row in rows] == [None, None, None]
    assert [row.population for row in rows] == pytest.approx([8.4, 0.8, 0.8])
    assert [row.laplacian_integral for row in rows] == pytest.approx([1.0e-4, -5.0e-5, -5.0e-5])


def test_parse_critic2_molecular_properties_without_volume() -> None:
    module = _module()
    text = """* Integration of basin properties by bisection
* List of attractors integrated
# Id   cp   ncp   Name  Z   mult           Position (bohr)
  1    1    1      O_   8   1     0.0000000    0.0000000    0.0000000

* Integrated atomic properties
# (See key above for interpretation of column headings.)
# Integrable properties 1 to 2
# Id   cp   ncp   Name  Z   mult       Pop             Lap
  1    1    1      O_   8   1    8.92438605E+00  1.36704494E-03
----------------------------------------------------------------
  Sum                            8.92438605E+00  1.36704494E-03
"""
    rows = module.parse_critic2_basin_output(text)

    assert len(rows) == 1
    assert rows[0].volume is None
    assert rows[0].population == pytest.approx(8.92438605)
    assert rows[0].laplacian_integral == pytest.approx(1.36704494e-3)


def test_critic2_input_uses_explicit_population_focused_radial_controls(tmp_path: Path) -> None:
    module = _module()
    fchk = tmp_path / "water.fchk"
    fchk.write_text("fixture", encoding="utf-8")

    script = module.build_critic2_input(fchk, lebedev_points=590)

    assert "int_radial type qags" in script.lower()
    assert "abserr 1e-10" in script.lower()
    assert "relerr 1e-10" in script.lower()
    assert "errprop 2" in script.lower()
    assert "prec 1e-6" in script.lower()
    assert "integrals lebedev 590" in script.lower()


def test_external_reference_population_closure_is_required() -> None:
    module = _module()

    with pytest.raises(ValueError, match="closure|electron"):
        module.validate_reference_population_closure(
            population_sum_e=9.423414138,
            expected_electrons_e=10.0,
            tolerance_e=0.01,
            case_id="water",
        )

    assert module.validate_reference_population_closure(
        population_sum_e=9.99944533,
        expected_electrons_e=10.0,
        tolerance_e=0.01,
        case_id="methane",
    ) == pytest.approx(0.00055467)


@pytest.mark.parametrize(
    "populations",
    [[8.92438591, 0.249463015, 0.249565213], [float("nan"), 0.5, 0.5], [11.0, -0.5, -0.5]],
)
def test_independent_reference_rejects_bad_closure_or_nonphysical_values(populations) -> None:
    module = _module()
    with pytest.raises(ValueError, match="closure|finite|negative"):
        module.validate_reference_populations(populations, expected_electrons=10.0)


def test_independent_reference_records_closure_without_renormalization() -> None:
    module = _module()
    populations = [8.4, 0.8, 0.799]
    diagnostics = module.validate_reference_populations(populations, expected_electrons=10.0)
    assert diagnostics["electron_count_residual_e"] == pytest.approx(0.001)
    assert populations == [8.4, 0.8, 0.799]


def test_comparison_gate_rejects_bad_convergence_despite_electron_closure():
    module = _module()
    medium = np.asarray([6.0107921593470595, .996812988554884, .996812988554884, .996812988554884, .996812988554884])
    fine = np.asarray([6.0460756290778415, .988471889376745, .988471889376745, .988471889376745, .988471889376745])
    report = module.assess_basin_convergence(
        reference_populations=fine.tolist(), medium_populations=medium.tolist(),
        fine_populations=fine.tolist(), fine_electron_residual=.00004,
        fine_charge_residual=.00004, fine_unresolved_electrons=1e-9,
    )
    assert not report['passed']
    assert report['checks']['grid_refinement'] is False
    assert report['checks']['reference_agreement'] is True


def test_comparison_gate_requires_independent_agreement_and_all_declared_rules():
    module = _module()
    kwargs = dict(reference_populations=[8.4, .8, .8], medium_populations=[8.4, .8, .8],
                  fine_populations=[8.405, .7975, .7975], fine_electron_residual=.001,
                  fine_charge_residual=.001, fine_unresolved_electrons=.0001)
    assert module.assess_basin_convergence(**kwargs)['passed']
    for key, value in [('fine_populations', [8.45, .775, .775]), ('fine_electron_residual', .1),
                       ('fine_charge_residual', .1), ('fine_unresolved_electrons', .1)]:
        assert not module.assess_basin_convergence(**{**kwargs, key: value})['passed']


def test_generator_preserves_raw_evidence_but_does_not_publish_bad_reference(tmp_path, monkeypatch):
    import hashlib
    import json

    module = _module()
    source = tmp_path / 'water.fchk'
    source.write_text('test input')
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({'cases': [{'id': 'water', 'status': 'active',
        'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}]}))
    stdout = FIXTURE.read_text().replace('8.40000000E+00', '8.00000000E+00')
    monkeypatch.setattr(module, '_run_critic2', lambda *a, **kw: ('input', stdout, ''))
    monkeypatch.setattr(module, '_calculation_geometry', lambda path: (
        np.asarray([8, 1, 1]), np.asarray([[0., 0., 0.], [1.43, 1.1, 0.], [-1.43, 1.1, 0.]]), 0))
    output = tmp_path / 'reference.json'
    with pytest.raises(ValueError, match='closure'):
        module.generate_reference(critic2=tmp_path / 'critic2', fixtures=[('water', source)],
            manifest=manifest, output=output, critic_home=None, lebedev_points=590,
            mapping_tolerance_bohr=.35, source_commit=module.CRITIC2_COMMIT,
            build_description='test double; not scientific reference')
    assert not output.exists()
    assert (tmp_path / 'reference.raw/water.out').read_text() == stdout


@pytest.mark.parametrize('partial_grid', ['medium', 'fine'])
def test_comparison_cannot_promote_engine_partial_results_to_pass(tmp_path, monkeypatch, partial_grid):
    import hashlib
    from types import SimpleNamespace

    import openwfn.api

    module = _module()
    source = tmp_path / 'molecule.fchk'
    source.write_text('fixture')
    count = 0

    def analyze(**kwargs):
        nonlocal count
        name = ['coarse', 'medium', 'fine'][count]
        count += 1
        record = {'status': 'partial' if name == partial_grid else 'success',
                  'data': {'atoms': [{'electron_population': 1.}, {'electron_population': 1.}],
                           'diagnostics': {'electron_count_residual': 0., 'charge_closure_residual': 0.,
                                           'unresolved_electrons': 0., 'population_partition_residual': 1e-7}}}
        return SimpleNamespace(as_dict=lambda: record)

    monkeypatch.setattr(openwfn.api, 'load', lambda path: SimpleNamespace(qtaim_basins=analyze))
    output = tmp_path / 'comparison.json'
    report = module.compare_openwfn_reference({'fixtures': [{'id': 'test', 'path': str(source),
        'sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'atomic_numbers': [1, 1],
        'expected_molecular_charge_e': 0, 'populations_e': [1., 1.]}]}, output)
    assert count == 3
    assert not report['passed']
    assert not report['fixtures'][0]['assessment']['passed']
    assert output.exists()
