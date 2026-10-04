import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from openwfn.analysis.hirshfeld_reference import (
    HirshfeldReferenceLibrary,
    ReferenceDensity,
    _load_hirshfeld_reference_library_from_directory,
    load_hirshfeld_reference_library,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_load_packaged_v1_library_and_lookup_supported_elements() -> None:
    library = load_hirshfeld_reference_library()

    assert isinstance(library, HirshfeldReferenceLibrary)
    assert library.library_id == "openwfn-hirshfeld-proatoms-v1"
    assert library.version == "v1"
    assert library.supported_elements == ("H", "C", "N", "O")
    assert len(library.library_sha256) == 64

    for symbol, atomic_number in {"H": 1, "C": 6, "N": 7, "O": 8}.items():
        reference = library.for_element(symbol)
        assert isinstance(reference, ReferenceDensity)
        assert reference.symbol == symbol
        assert reference.atomic_number == atomic_number
        assert reference.neutral_electrons == atomic_number
        assert reference.radius_bohr[0] == 0.0
        assert reference.radius_bohr[-1] == 40.0
        assert reference.tail_verified is True


def test_reference_density_evaluate_matches_grid_and_is_nonnegative_vectorized() -> None:
    reference = load_hirshfeld_reference_library().for_element("O")
    indices = np.array([0, 1, 10, 100, 1000, reference.radius_bohr.size - 1])
    radii = reference.radius_bohr[indices]

    exact = reference.evaluate(radii)
    np.testing.assert_allclose(exact, reference.density_e_per_bohr3[indices], rtol=0.0, atol=0.0)

    probes = np.linspace(0.0, reference.outer_radius_bohr, 2049)
    values = reference.evaluate(probes)
    assert values.shape == probes.shape
    assert np.all(np.isfinite(values))
    assert np.all(values >= 0.0)


def test_reference_density_interpolation_is_shape_preserving_between_nodes() -> None:
    reference = load_hirshfeld_reference_library().for_element("C")
    i = 750
    left_r = float(reference.radius_bohr[i])
    right_r = float(reference.radius_bohr[i + 1])
    midpoint = 0.5 * (left_r + right_r)
    left_density = float(reference.density_e_per_bohr3[i])
    right_density = float(reference.density_e_per_bohr3[i + 1])

    interpolated = float(reference.evaluate(np.array([midpoint]))[0])
    lower = min(left_density, right_density)
    upper = max(left_density, right_density)
    assert lower <= interpolated <= upper
    assert interpolated >= 0.0


def test_reference_density_tail_is_zero_only_after_verified_outer_grid() -> None:
    reference = load_hirshfeld_reference_library().for_element("N")

    values = reference.evaluate(
        np.array(
            [
                reference.outer_radius_bohr,
                reference.outer_radius_bohr + 1.0e-8,
                reference.outer_radius_bohr + 10.0,
            ]
        )
    )
    assert values[0] == reference.density_e_per_bohr3[-1]
    assert values[1] == 0.0
    assert values[2] == 0.0


def test_reference_density_rejects_negative_or_nonfinite_radius() -> None:
    reference = load_hirshfeld_reference_library().for_element("H")

    with pytest.raises(ValueError, match="non-negative"):
        reference.evaluate(np.array([-1.0e-6]))
    with pytest.raises(ValueError, match="finite"):
        reference.evaluate(np.array([np.nan]))


def test_library_rejects_unsupported_element_without_fallback() -> None:
    library = load_hirshfeld_reference_library()

    with pytest.raises(ValueError, match="Unsupported Hirshfeld reference element 'F'"):
        library.for_element("F")


def test_directory_loader_rejects_tampered_reference_hash(tmp_path: Path) -> None:
    source = load_hirshfeld_reference_library()
    manifest = json.loads(source.manifest_json)
    element = "H"
    record = manifest["elements"][element]

    data_path = tmp_path / record["file"]
    np.savez(
        data_path,
        radius_bohr=np.array([0.0, 1.0, 40.0]),
        density_e_per_bohr3=np.array([1.0, 0.1, 0.0]),
    )
    assert _sha256(data_path) != record["sha256"]
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        _load_hirshfeld_reference_library_from_directory(tmp_path)


def test_directory_loader_rejects_malformed_manifest(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text(
        json.dumps({"schema_version": "1.0", "library_id": "broken", "elements": {}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="supported_elements"):
        _load_hirshfeld_reference_library_from_directory(tmp_path)


def test_directory_loader_rejects_unverified_tail_policy(tmp_path: Path) -> None:
    radius = np.array([0.0, 1.0, 40.0])
    density = np.array([1.0, 0.1, 1.0e-5])
    data_path = tmp_path / "H.npz"
    np.savez(data_path, radius_bohr=radius, density_e_per_bohr3=density)
    manifest = {
        "schema_version": "1.0",
        "library_id": "test-library",
        "supported_elements": ["H"],
        "units": {"radius": "bohr", "density": "electron/bohr^3"},
        "tail_criterion": {"density_e_per_bohr3": 1.0e-12, "outer_radius_bohr": 40.0},
        "elements": {
            "H": {
                "atomic_number": 1,
                "neutral_electrons": 1,
                "file": "H.npz",
                "sha256": _sha256(data_path),
                "tail_density_e_per_bohr3": 1.0e-5,
            }
        },
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="tail criterion"):
        _load_hirshfeld_reference_library_from_directory(tmp_path)
