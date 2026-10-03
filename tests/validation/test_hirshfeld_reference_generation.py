import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
REFERENCE_DIR = ROOT / "src" / "openwfn" / "reference_data" / "hirshfeld" / "v1"
MANIFEST = REFERENCE_DIR / "manifest.json"
EXPECTED = {"H": 1, "C": 6, "N": 7, "O": 8}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _trapezoid(values: np.ndarray, coordinates: np.ndarray) -> float:
    trapezoid = getattr(np, "trapezoid", None)
    if trapezoid is not None:
        return float(trapezoid(values, coordinates))
    return float(np.trapz(values, coordinates))  # type: ignore[attr-defined]


def test_hirshfeld_reference_manifest_and_files_are_provenance_complete() -> None:
    assert MANIFEST.is_file()
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert payload["library_id"] == "openwfn-hirshfeld-proatoms-v1"
    assert payload["schema_version"] == "1.0"
    assert payload["generator"]["software"] == "PySCF"
    assert payload["generator"]["software_version"] == "2.12.1"
    assert payload["generator"]["method"] == "spherical fractional-occupation RKS/PBE"
    assert payload["generator"]["atom_solver"] == "pyscf.scf.atom_ks.get_atm_nrks"
    assert payload["generator"]["fractional_occupations"] is True
    assert payload["generator"]["basis"] == "aug-cc-pVQZ"
    assert payload["generator"]["atomic_grid"] == {
        "radial_points": 100,
        "angular_points": 434,
    }
    assert payload["units"] == {
        "radius": "bohr",
        "density": "electron/bohr^3",
    }
    assert payload["supported_elements"] == ["H", "C", "N", "O"]
    assert payload["redistribution"]["status"] == "repository-generated scientific data"

    records = payload["elements"]
    assert set(records) == set(EXPECTED)

    for symbol, atomic_number in EXPECTED.items():
        record = records[symbol]
        assert record["atomic_number"] == atomic_number
        assert record["neutral_electrons"] == atomic_number
        assert record["occupation_model"] == "spherical fractional occupation"
        data_path = REFERENCE_DIR / record["file"]
        assert data_path.is_file()
        assert record["sha256"] == _sha256(data_path)


def test_hirshfeld_reference_arrays_are_normalized_finite_and_nonnegative() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    for symbol, atomic_number in EXPECTED.items():
        data_path = REFERENCE_DIR / payload["elements"][symbol]["file"]
        with np.load(data_path, allow_pickle=False) as archive:
            radius = np.asarray(archive["radius_bohr"], dtype=float)
            density = np.asarray(archive["density_e_per_bohr3"], dtype=float)

        assert radius.ndim == 1
        assert density.shape == radius.shape
        assert radius.size >= 512
        assert radius[0] >= 0.0
        assert radius[-1] >= 40.0
        assert np.all(np.isfinite(radius))
        assert np.all(np.isfinite(density))
        assert np.all(np.diff(radius) > 0.0)
        assert np.all(density >= 0.0)

        electron_count = 4.0 * np.pi * _trapezoid(density * radius * radius, radius)
        assert abs(float(electron_count) - atomic_number) <= 1.0e-6


def test_hirshfeld_reference_manifest_records_generation_and_tail_checks() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert payload["radial_grid"]["outer_radius_bohr"] >= 40.0
    assert payload["radial_grid"]["points"] >= 512
    assert payload["tail_criterion"]["density_e_per_bohr3"] <= 1.0e-12
    assert payload["normalization_tolerance_e"] == 1.0e-6

    for symbol in EXPECTED:
        record = payload["elements"][symbol]
        assert record["normalization_error_e"] <= payload["normalization_tolerance_e"]
        assert record["tail_density_e_per_bohr3"] <= payload["tail_criterion"]["density_e_per_bohr3"]
