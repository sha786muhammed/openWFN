#!/usr/bin/env python3
"""Generate openWFN's versioned neutral-atom Hirshfeld reference densities.

This script is an offline scientific-data generator, not a runtime dependency.
It requires the exact PySCF version recorded below and writes repository-owned
radial density data suitable for redistribution with openWFN.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PYSCF_VERSION = "2.12.1"
LIBRARY_ID = "openwfn-hirshfeld-proatoms-v1"
SCHEMA_VERSION = "1.0"
METHOD = "spherical fractional-occupation RKS/PBE"
ATOM_SOLVER = "pyscf.scf.atom_ks.get_atm_nrks"
BASIS = "aug-cc-pVQZ"
ATOMIC_GRID = (100, 434)
OUTER_RADIUS_BOHR = 40.0
RADIAL_POINTS = 8193
THETA_POINTS = 16
PHI_POINTS = 32
NORMALIZATION_TOLERANCE_E = 1.0e-6
TAIL_DENSITY_TOLERANCE = 1.0e-12
NEGATIVE_NOISE_TOLERANCE = 1.0e-12
RADIAL_CHUNK = 32

# The first reference library is deliberately limited to the elements covered
# by the existing everyday-QC validation corpus.
ATOMS: dict[str, int] = {
    "H": 1,
    "C": 6,
    "N": 7,
    "O": 8,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _trapezoid(values: np.ndarray, coordinates: np.ndarray) -> float:
    """Integrate with NumPy 1.x/2.x compatibility without changing the rule."""

    trapezoid = getattr(np, "trapezoid", None)
    if trapezoid is not None:
        return float(trapezoid(values, coordinates))
    return float(np.trapz(values, coordinates))  # type: ignore[attr-defined]


def _angular_grid() -> tuple[np.ndarray, np.ndarray]:
    """Return deterministic unit vectors and normalized spherical-average weights."""

    mu, mu_weights = np.polynomial.legendre.leggauss(THETA_POINTS)
    phi = 2.0 * np.pi * np.arange(PHI_POINTS, dtype=float) / PHI_POINTS
    vectors: list[tuple[float, float, float]] = []
    weights: list[float] = []
    for z, w_mu in zip(mu, mu_weights):
        radius_xy = math.sqrt(max(0.0, 1.0 - float(z) ** 2))
        for angle in phi:
            vectors.append(
                (
                    radius_xy * math.cos(float(angle)),
                    radius_xy * math.sin(float(angle)),
                    float(z),
                )
            )
            # dOmega/(4*pi): w_mu * (2*pi/Nphi) / (4*pi)
            weights.append(float(w_mu) / (2.0 * PHI_POINTS))
    result_vectors = np.asarray(vectors, dtype=float)
    result_weights = np.asarray(weights, dtype=float)
    if not np.isclose(float(np.sum(result_weights)), 1.0, atol=1e-14):
        raise RuntimeError("Angular-average weights do not sum to one.")
    return result_vectors, result_weights


def _radial_grid() -> np.ndarray:
    """Dense cubic-mapped grid with strong near-nuclear resolution and a 40 bohr tail."""

    t = np.linspace(0.0, 1.0, RADIAL_POINTS, dtype=float)
    return OUTER_RADIUS_BOHR * t**3


def _build_atom(
    symbol: str,
    atomic_number: int,
) -> tuple[object, np.ndarray, float, np.ndarray]:
    """Return molecule, spherical fractional-occupation AO density, energy and occupations."""

    try:
        import pyscf
        from pyscf import gto, lib
        from pyscf.scf import atom_ks
    except ImportError as exc:  # pragma: no cover - exercised in generator environments
        raise RuntimeError(f"PySCF {PYSCF_VERSION} is required to generate the v1 library.") from exc

    if pyscf.__version__ != PYSCF_VERSION:
        raise RuntimeError(
            f"Reference generation requires PySCF {PYSCF_VERSION}; found {pyscf.__version__}."
        )

    # Fix PySCF's linear-algebra thread count so the versioned reference-data
    # generator is reproducible across CI hosts. get_atm_nrks then constructs
    # AtomSphericAverageRKS internally, uses electron-parity spin and spherical
    # fractional occupations, and applies its atomic ADIIS/VSAP machinery.
    lib.num_threads(1)
    mol = gto.M(
        atom=f"{symbol} 0 0 0",
        basis=BASIS,
        charge=0,
        spin=atomic_number % 2,
        unit="Bohr",
        cart=False,
        verbose=0,
    )
    atomic_results = atom_ks.get_atm_nrks(mol, xc="PBE", grid=ATOMIC_GRID)
    try:
        energy, _mo_energy, mo_coeff, mo_occ = atomic_results[symbol]
    except KeyError as exc:
        raise RuntimeError(f"PySCF atomic solver did not return a {symbol} record.") from exc

    occupations = np.asarray(mo_occ, dtype=float)
    coefficients = np.asarray(mo_coeff, dtype=float)
    if coefficients.ndim != 2 or occupations.ndim != 1:
        raise RuntimeError(f"Unexpected PySCF atomic orbital result for {symbol}.")
    if coefficients.shape[1] != occupations.size:
        raise RuntimeError(f"Atomic coefficient/occupation dimensions disagree for {symbol}.")
    occupied_electrons = float(np.sum(occupations))
    if abs(occupied_electrons - atomic_number) > 1.0e-10:
        raise RuntimeError(
            f"{symbol} fractional occupations sum to {occupied_electrons:.12g}, "
            f"expected {atomic_number}."
        )
    density_matrix = (coefficients * occupations[None, :]) @ coefficients.T
    if not np.all(np.isfinite(density_matrix)) or not np.isfinite(float(energy)):
        raise RuntimeError(f"Non-finite spherical atomic result for {symbol}.")
    return mol, density_matrix, float(energy), occupations


def _spherical_density(
    mol: object,
    density_matrix: np.ndarray,
    radius_bohr: np.ndarray,
) -> np.ndarray:
    from pyscf.dft import numint

    directions, angular_weights = _angular_grid()
    dm = np.asarray(density_matrix, dtype=float)
    if dm.ndim != 2:
        raise RuntimeError(f"Unexpected PySCF density-matrix shape: {dm.shape!r}")

    density = np.empty_like(radius_bohr)
    for start in range(0, radius_bohr.size, RADIAL_CHUNK):
        stop = min(radius_bohr.size, start + RADIAL_CHUNK)
        radii = radius_bohr[start:stop]
        points = (radii[:, None, None] * directions[None, :, :]).reshape(-1, 3)
        ao = numint.eval_ao(mol, points, deriv=0)
        rho = np.asarray(numint.eval_rho(mol, ao, dm, xctype="LDA"), dtype=float)
        rho = rho.reshape(radii.size, directions.shape[0])
        density[start:stop] = rho @ angular_weights

    minimum = float(np.min(density))
    if minimum < -NEGATIVE_NOISE_TOLERANCE:
        raise RuntimeError(f"Spherical density became materially negative: {minimum:.6e}")
    # Only remove roundoff-scale negative noise; physical/provenance values are otherwise unchanged.
    return np.maximum(density, 0.0)


def _write_npz(path: Path, radius_bohr: np.ndarray, density: np.ndarray) -> None:
    np.savez(
        path,
        radius_bohr=np.asarray(radius_bohr, dtype=np.float64),
        density_e_per_bohr3=np.asarray(density, dtype=np.float64),
    )


def generate(output_dir: Path) -> dict[str, object]:
    import pyscf

    if pyscf.__version__ != PYSCF_VERSION:
        raise RuntimeError(
            f"Reference generation requires PySCF {PYSCF_VERSION}; found {pyscf.__version__}."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    radius = _radial_grid()
    element_records: dict[str, object] = {}

    for symbol, atomic_number in ATOMS.items():
        mol, density_matrix, energy, occupations = _build_atom(symbol, atomic_number)
        density = _spherical_density(mol, density_matrix, radius)
        electron_count = 4.0 * np.pi * _trapezoid(density * radius * radius, radius)
        normalization_error = abs(electron_count - atomic_number)
        tail_density = float(density[-1])
        if normalization_error > NORMALIZATION_TOLERANCE_E:
            raise RuntimeError(
                f"{symbol} radial density normalization error {normalization_error:.6e} e exceeds "
                f"{NORMALIZATION_TOLERANCE_E:.1e} e. Increase generator resolution; do not rescale."
            )
        if tail_density > TAIL_DENSITY_TOLERANCE:
            raise RuntimeError(
                f"{symbol} density at {OUTER_RADIUS_BOHR:g} bohr is {tail_density:.6e}, above "
                f"the tail criterion {TAIL_DENSITY_TOLERANCE:.1e}."
            )

        filename = f"{symbol}.npz"
        data_path = output_dir / filename
        _write_npz(data_path, radius, density)
        element_records[symbol] = {
            "atomic_number": atomic_number,
            "neutral_electrons": atomic_number,
            "occupation_model": "spherical fractional occupation",
            "nonzero_orbital_occupations": [
                float(value) for value in occupations if abs(float(value)) > 1.0e-14
            ],
            "file": filename,
            "sha256": _sha256(data_path),
            "scf_energy_hartree": energy,
            "integrated_electrons": electron_count,
            "normalization_error_e": normalization_error,
            "tail_density_e_per_bohr3": tail_density,
        }

    manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "library_id": LIBRARY_ID,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "supported_elements": list(ATOMS),
        "generator": {
            "software": "PySCF",
            "software_version": PYSCF_VERSION,
            "numpy_version": np.__version__,
            "method": METHOD,
            "atom_solver": ATOM_SOLVER,
            "basis": BASIS,
            "fractional_occupations": True,
            "atomic_grid": {
                "radial_points": ATOMIC_GRID[0],
                "angular_points": ATOMIC_GRID[1],
            },
            "linear_algebra_threads": 1,
            "spherical_average": {
                "theta_quadrature": "Gauss-Legendre in cos(theta)",
                "theta_points": THETA_POINTS,
                "phi_quadrature": "uniform periodic",
                "phi_points": PHI_POINTS,
            },
            "density_rescaling": False,
        },
        "units": {
            "radius": "bohr",
            "density": "electron/bohr^3",
        },
        "radial_grid": {
            "mapping": "r = Rmax * t^3, t uniformly spaced on [0,1]",
            "points": RADIAL_POINTS,
            "outer_radius_bohr": OUTER_RADIUS_BOHR,
        },
        "normalization_tolerance_e": NORMALIZATION_TOLERANCE_E,
        "tail_criterion": {
            "density_e_per_bohr3": TAIL_DENSITY_TOLERANCE,
            "outer_radius_bohr": OUTER_RADIUS_BOHR,
        },
        "redistribution": {
            "status": "repository-generated scientific data",
            "license": "MIT with the openWFN repository; values generated from PySCF calculations",
            "copied_external_dataset": False,
        },
        "elements": element_records,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("src/openwfn/reference_data/hirshfeld/v1"),
    )
    args = parser.parse_args()
    manifest = generate(args.output_dir)
    print(json.dumps({"library_id": manifest["library_id"], "output": str(args.output_dir)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
