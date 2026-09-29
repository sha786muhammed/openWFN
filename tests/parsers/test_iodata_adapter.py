from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from openwfn.capabilities import infer_capabilities
from openwfn.constants import BOHR_TO_ANGSTROM


def _fake_shell() -> SimpleNamespace:
    return SimpleNamespace(
        icenter=0,
        angmoms=np.array([0]),
        kinds=["c"],
        exponents=np.array([1.0]),
        coeffs=np.array([[1.0]]),
    )


def _fake_basis() -> SimpleNamespace:
    return SimpleNamespace(
        shells=[_fake_shell()],
        conventions={(0, "c"): ["1"]},
        primitive_normalization="L2",
        nbasis=1,
    )


def _fake_restricted_mo() -> SimpleNamespace:
    return SimpleNamespace(
        kind="restricted",
        norba=1,
        norbb=1,
        coeffsa=np.array([[1.0]]),
        coeffsb=np.array([[1.0]]),
        energiesa=np.array([-0.5]),
        energiesb=np.array([-0.5]),
        occsa=np.array([1.0]),
        occsb=np.array([1.0]),
        spinpol=0.0,
    )


def _fake_loaded(**overrides) -> SimpleNamespace:
    payload = {
        "atcoords": np.array([[0.0, 0.0, 0.0]]),
        "atnums": np.array([1]),
        "atcorenums": np.array([1.0]),
        "charge": 0.0,
        "spinpol": 0.0,
        "energy": -0.5,
        "title": "hydrogen fixture",
        "cellvecs": None,
        "cube": None,
        "core_energy": None,
        "one_ints": {},
        "two_ints": {},
        "nelec": 1,
        "obasis": None,
        "obasis_name": None,
        "mo": None,
        "bonds": None,
        "extra": {},
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_importing_adapter_is_lazy_about_iodata() -> None:
    sys.modules.pop("openwfn.adapters.iodata", None)
    sys.modules.pop("iodata", None)

    importlib.import_module("openwfn.adapters.iodata")

    assert "iodata" not in sys.modules


def test_load_iodata_xyz_normalizes_units_and_records_backend(tmp_path: Path) -> None:
    from openwfn.adapters.iodata import load_iodata

    source = tmp_path / "water.xyz"
    source.write_text("1\nsynthetic openWFN fixture\nH 1.0 0.0 0.0\n", encoding="utf-8")

    data = load_iodata(source, format_id="xyz")

    assert data.structure is not None
    assert data.structure.coordinates[0][0] == pytest.approx(1.0)
    assert data.provenance is not None
    assert data.provenance.source_format == "xyz"
    assert data.provenance.parser == "openwfn-iodata-adapter"
    assert data.provenance.backend == "iodata"
    assert data.provenance.backend_version == "1.0.1"
    assert any("bohr -> angstrom" in item for item in data.provenance.transformations)


def test_complete_wavefunction_maps_to_existing_calculation_model(tmp_path: Path) -> None:
    from openwfn.adapters.iodata import adapt_iodata_object

    source = tmp_path / "water.molden"
    source.write_text("synthetic\n", encoding="utf-8")
    loaded = _fake_loaded(obasis=_fake_basis(), mo=_fake_restricted_mo())

    data = adapt_iodata_object(loaded, source, format_id="molden", backend_version="1.0.1")

    assert data.calculation is not None
    assert data.basis is not None
    assert data.basis.n_functions == 1
    assert data.alpha_orbitals is not None
    assert data.alpha_orbitals.energies == pytest.approx((-0.5,))
    assert data.alpha_orbitals.occupations == pytest.approx((2.0,))
    assert data.molecule.atoms[0].nuclear_charge == pytest.approx(1.0)


def test_periodic_grid_and_integral_components_are_preserved_without_fabrication(
    tmp_path: Path,
) -> None:
    from openwfn.adapters.iodata import adapt_iodata_object

    source = tmp_path / "mixed.fixture"
    source.write_text("synthetic\n", encoding="utf-8")
    cube = SimpleNamespace(
        origin=np.array([0.0, 0.0, 0.0]),
        axes=np.eye(3),
        data=np.array([[[0.25]]]),
        shape=(1, 1, 1),
    )
    loaded = _fake_loaded(
        atcoords=np.array([[1.0, 0.0, 0.0]]),
        cellvecs=np.eye(3) * 5.0,
        cube=cube,
        one_ints={"core_mo": np.array([[1.25]])},
        two_ints={"two_mo": np.array([[[[0.5]]]])},
        core_energy=0.125,
        obasis=None,
        mo=None,
    )

    data = adapt_iodata_object(loaded, source, format_id="test", backend_version="1.0.1")

    assert data.calculation is None
    assert data.periodic is not None
    assert data.periodic.cell_vectors[0][0] == pytest.approx(5.0 * BOHR_TO_ANGSTROM)
    assert len(data.grids) == 1
    assert data.grids[0].origin == pytest.approx((0.0, 0.0, 0.0))
    assert data.integrals is not None
    assert data.integrals.n_orbitals == 1
    assert data.integrals.one_electron[0].indices == (0, 0)
    assert data.integrals.two_electron[0].indices == (0, 0, 0, 0)


def test_partial_wavefunction_withholds_calculation_and_capabilities(tmp_path: Path) -> None:
    from openwfn.adapters.iodata import adapt_iodata_object

    source = tmp_path / "partial.molden"
    source.write_text("synthetic\n", encoding="utf-8")
    loaded = _fake_loaded(obasis=_fake_basis(), mo=None)

    data = adapt_iodata_object(loaded, source, format_id="molden", backend_version="1.0.1")
    capabilities = infer_capabilities(data)

    assert data.calculation is None
    assert capabilities["structure"].state == "available"
    assert capabilities["alpha_orbitals"].state == "missing"
    assert data.provenance is not None
    assert any("wavefunction" in warning.lower() for warning in data.provenance.warnings)
