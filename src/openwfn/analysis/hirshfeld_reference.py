"""Versioned neutral-atom reference densities for native Hirshfeld analysis."""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Mapping

import numpy as np

_REFERENCE_ROOT = ("reference_data", "hirshfeld")
_EXPECTED_UNITS = {"radius": "bohr", "density": "electron/bohr^3"}


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _require_mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Hirshfeld reference {name} must be a JSON object.")
    return value


def _require_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Hirshfeld reference {name} must be numeric.")
    result = float(value)
    if not np.isfinite(result):
        raise ValueError(f"Hirshfeld reference {name} must be finite.")
    return result


def _canonical_symbol(symbol: str) -> str:
    stripped = symbol.strip()
    if not stripped:
        return stripped
    return stripped[0].upper() + stripped[1:].lower()


@dataclass(frozen=True, slots=True)
class ReferenceDensity:
    """One spherical neutral free-atom radial electron density."""

    symbol: str
    atomic_number: int
    neutral_electrons: int
    radius_bohr: np.ndarray
    density_e_per_bohr3: np.ndarray
    file_sha256: str
    tail_density_e_per_bohr3: float
    tail_threshold_e_per_bohr3: float
    outer_radius_bohr: float
    tail_verified: bool

    def evaluate(self, radius_bohr: np.ndarray) -> np.ndarray:
        """Evaluate the nonnegative radial density by piecewise-linear interpolation."""

        query = np.asarray(radius_bohr, dtype=float)
        if not np.all(np.isfinite(query)):
            raise ValueError("Hirshfeld reference radii must be finite.")
        if np.any(query < 0.0):
            raise ValueError("Hirshfeld reference radii must be non-negative.")
        if not self.tail_verified:
            raise ValueError("Hirshfeld reference tail criterion is not verified.")

        shape = query.shape
        flat = query.reshape(-1)
        values = np.interp(
            flat,
            self.radius_bohr,
            self.density_e_per_bohr3,
            left=float(self.density_e_per_bohr3[0]),
            right=0.0,
        )
        values = np.maximum(values, 0.0)
        return values.reshape(shape)


@dataclass(frozen=True, slots=True)
class HirshfeldReferenceLibrary:
    """A validated-on-load collection of versioned neutral pro-atom densities."""

    version: str
    library_id: str
    library_sha256: str
    supported_elements: tuple[str, ...]
    references: Mapping[str, ReferenceDensity]
    manifest_json: str

    def for_element(self, symbol: str) -> ReferenceDensity:
        canonical = _canonical_symbol(symbol)
        try:
            return self.references[canonical]
        except KeyError as exc:
            supported = ", ".join(self.supported_elements)
            raise ValueError(
                f"Unsupported Hirshfeld reference element '{canonical}'. "
                f"Supported elements: {supported}."
            ) from exc


def _parse_manifest(manifest_bytes: bytes) -> tuple[str, Mapping[str, Any]]:
    try:
        manifest_json = manifest_bytes.decode("utf-8")
        payload = json.loads(manifest_json)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Hirshfeld reference manifest is not valid UTF-8 JSON.") from exc
    manifest = _require_mapping(payload, "manifest")

    required = (
        "schema_version",
        "library_id",
        "supported_elements",
        "units",
        "tail_criterion",
        "elements",
    )
    missing = [name for name in required if name not in manifest]
    if missing:
        raise ValueError(
            "Hirshfeld reference manifest is missing required field(s): " + ", ".join(missing)
        )

    if manifest["schema_version"] != "1.0":
        raise ValueError(
            f"Unsupported Hirshfeld reference schema version {manifest['schema_version']!r}."
        )
    if not isinstance(manifest["library_id"], str) or not manifest["library_id"].strip():
        raise ValueError("Hirshfeld reference library_id must be a non-empty string.")
    if manifest["units"] != _EXPECTED_UNITS:
        raise ValueError(f"Hirshfeld reference units must be {_EXPECTED_UNITS!r}.")

    supported = manifest["supported_elements"]
    if (
        not isinstance(supported, list)
        or not supported
        or not all(isinstance(symbol, str) and symbol for symbol in supported)
        or len(set(supported)) != len(supported)
    ):
        raise ValueError("Hirshfeld reference supported_elements must be a non-empty unique list.")
    elements = _require_mapping(manifest["elements"], "elements")
    if set(elements) != set(supported):
        raise ValueError("Hirshfeld reference elements must exactly match supported_elements.")

    return manifest_json, manifest


def _load_arrays(content: bytes, symbol: str) -> tuple[np.ndarray, np.ndarray]:
    try:
        with np.load(io.BytesIO(content), allow_pickle=False) as archive:
            radius = np.asarray(archive["radius_bohr"], dtype=float).copy()
            density = np.asarray(archive["density_e_per_bohr3"], dtype=float).copy()
    except (KeyError, OSError, ValueError) as exc:
        raise ValueError(f"Malformed Hirshfeld reference data for {symbol}.") from exc

    if radius.ndim != 1 or density.ndim != 1 or radius.size < 2 or density.shape != radius.shape:
        raise ValueError(f"Malformed Hirshfeld reference array shapes for {symbol}.")
    if not np.all(np.isfinite(radius)) or not np.all(np.isfinite(density)):
        raise ValueError(f"Hirshfeld reference arrays for {symbol} must be finite.")
    if radius[0] < 0.0 or not np.all(np.diff(radius) > 0.0):
        raise ValueError(f"Hirshfeld reference radii for {symbol} must be non-negative and increasing.")
    if np.any(density < 0.0):
        raise ValueError(f"Hirshfeld reference density for {symbol} must be nonnegative.")

    radius.setflags(write=False)
    density.setflags(write=False)
    return radius, density


def _build_library(
    *,
    version: str,
    manifest_bytes: bytes,
    read_file: Any,
) -> HirshfeldReferenceLibrary:
    manifest_json, manifest = _parse_manifest(manifest_bytes)
    supported = tuple(manifest["supported_elements"])
    elements = _require_mapping(manifest["elements"], "elements")
    tail = _require_mapping(manifest["tail_criterion"], "tail_criterion")
    if "density_e_per_bohr3" not in tail or "outer_radius_bohr" not in tail:
        raise ValueError("Hirshfeld reference tail_criterion is incomplete.")
    tail_threshold = _require_number(
        tail["density_e_per_bohr3"], "tail_criterion.density_e_per_bohr3"
    )
    tail_outer = _require_number(tail["outer_radius_bohr"], "tail_criterion.outer_radius_bohr")
    if tail_threshold < 0.0 or tail_outer <= 0.0:
        raise ValueError("Hirshfeld reference tail criterion must be positive/physical.")

    references: dict[str, ReferenceDensity] = {}
    file_hashes: list[str] = []
    for symbol in supported:
        record = _require_mapping(elements[symbol], f"elements.{symbol}")
        required_record = (
            "atomic_number",
            "neutral_electrons",
            "file",
            "sha256",
            "tail_density_e_per_bohr3",
        )
        missing = [name for name in required_record if name not in record]
        if missing:
            raise ValueError(
                f"Hirshfeld reference record for {symbol} is missing: {', '.join(missing)}"
            )
        atomic_number = record["atomic_number"]
        neutral_electrons = record["neutral_electrons"]
        if (
            isinstance(atomic_number, bool)
            or not isinstance(atomic_number, int)
            or atomic_number <= 0
            or isinstance(neutral_electrons, bool)
            or not isinstance(neutral_electrons, int)
            or neutral_electrons <= 0
        ):
            raise ValueError(f"Invalid Hirshfeld atomic metadata for {symbol}.")
        filename = record["file"]
        expected_hash = record["sha256"]
        if not isinstance(filename, str) or not filename.endswith(".npz"):
            raise ValueError(f"Invalid Hirshfeld reference filename for {symbol}.")
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            raise ValueError(f"Invalid Hirshfeld SHA-256 metadata for {symbol}.")

        content = read_file(filename)
        actual_hash = _sha256_bytes(content)
        if actual_hash != expected_hash:
            raise ValueError(
                f"Hirshfeld reference SHA-256 mismatch for {symbol}: "
                f"expected {expected_hash}, got {actual_hash}."
            )
        radius, density = _load_arrays(content, symbol)
        record_tail = _require_number(
            record["tail_density_e_per_bohr3"], f"elements.{symbol}.tail_density_e_per_bohr3"
        )
        if not np.isclose(float(radius[-1]), tail_outer, rtol=0.0, atol=1.0e-12):
            raise ValueError(f"Hirshfeld reference outer radius mismatch for {symbol}.")
        actual_tail = float(density[-1])
        if record_tail > tail_threshold or actual_tail > tail_threshold:
            raise ValueError(
                f"Hirshfeld reference tail criterion failed for {symbol}: "
                f"density at {tail_outer:g} bohr is not negligible."
            )
        if not np.isclose(record_tail, actual_tail, rtol=1.0e-12, atol=0.0):
            raise ValueError(f"Hirshfeld reference tail metadata mismatch for {symbol}.")

        references[symbol] = ReferenceDensity(
            symbol=symbol,
            atomic_number=atomic_number,
            neutral_electrons=neutral_electrons,
            radius_bohr=radius,
            density_e_per_bohr3=density,
            file_sha256=actual_hash,
            tail_density_e_per_bohr3=actual_tail,
            tail_threshold_e_per_bohr3=tail_threshold,
            outer_radius_bohr=tail_outer,
            tail_verified=True,
        )
        file_hashes.append(f"{symbol}:{actual_hash}")

    library_digest = hashlib.sha256()
    library_digest.update(manifest_bytes)
    for value in file_hashes:
        library_digest.update(b"\0")
        library_digest.update(value.encode("ascii"))

    return HirshfeldReferenceLibrary(
        version=version,
        library_id=str(manifest["library_id"]),
        library_sha256=library_digest.hexdigest(),
        supported_elements=supported,
        references=references,
        manifest_json=manifest_json,
    )


def _load_hirshfeld_reference_library_from_directory(
    directory: Path,
    *,
    version: str = "v1",
) -> HirshfeldReferenceLibrary:
    """Load a reference library from a directory; primarily useful for validation tests."""

    root = Path(directory)
    manifest_path = root / "manifest.json"
    try:
        manifest_bytes = manifest_path.read_bytes()
    except OSError as exc:
        raise ValueError(f"Unable to read Hirshfeld reference manifest: {manifest_path}.") from exc

    def read_file(filename: str) -> bytes:
        try:
            return (root / filename).read_bytes()
        except OSError as exc:
            raise ValueError(f"Unable to read Hirshfeld reference data file {filename!r}.") from exc

    return _build_library(
        version=version,
        manifest_bytes=manifest_bytes,
        read_file=read_file,
    )


def load_hirshfeld_reference_library(version: str = "v1") -> HirshfeldReferenceLibrary:
    """Load and verify a packaged version of openWFN's neutral pro-atom library."""

    normalized = version.strip()
    if normalized != "v1":
        raise ValueError(f"Unsupported Hirshfeld reference library version {version!r}.")
    root = resources.files("openwfn")
    for component in (*_REFERENCE_ROOT, normalized):
        root = root.joinpath(component)
    try:
        manifest_bytes = root.joinpath("manifest.json").read_bytes()
    except (FileNotFoundError, OSError) as exc:
        raise ValueError(f"Packaged Hirshfeld reference library {normalized!r} is unavailable.") from exc

    def read_file(filename: str) -> bytes:
        try:
            return root.joinpath(filename).read_bytes()
        except (FileNotFoundError, OSError) as exc:
            raise ValueError(f"Unable to read packaged Hirshfeld reference data {filename!r}.") from exc

    return _build_library(
        version=normalized,
        manifest_bytes=manifest_bytes,
        read_file=read_file,
    )
