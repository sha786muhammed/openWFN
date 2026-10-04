#!/usr/bin/env python3
"""Independent and grid-convergence validation for native Hirshfeld charges.

The external comparison uses HORTON-PART only as a validation dependency. It is
not imported by ``src/openwfn`` and is not a runtime dependency of openWFN.
The exact openWFN v1 neutral pro-atom radial data are passed to HORTON-PART so
that the stockholder convention is held fixed while the molecular grid,
density evaluator, spline interpolation, and partition implementation are
independent.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
from pathlib import Path
from typing import Any

import numpy as np

from openwfn.analysis.atom_quadrature import AtomQuadratureSettings
from openwfn.analysis.hirshfeld import HirshfeldSettings
from openwfn.analysis.hirshfeld_reference import load_hirshfeld_reference_library
from openwfn.api import load

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "examples" / "everyday-qc"
REFERENCE_TOLERANCE_E = 1.0e-3
CONVERGENCE_TOLERANCE_E = 5.0e-4

CASES = {
    "water": CORPUS / "water.molden",
    "methane": CORPUS / "methane.molden",
    "ammonia": CORPUS / "ammonia.molden",
    "carbon_dioxide": CORPUS / "carbon_dioxide.molden",
    "benzene": CORPUS / "benzene.molden",
    "ethanol": CORPUS / "ethanol.molden",
    "ammonium_cation": CORPUS / "ammonium_cation.molden",
    "oxygen_triplet": CORPUS / "oxygen_triplet.molden",
    "oh_diffuse_uhf": CORPUS / "oh_diffuse_uhf.molden",
    "water_dimer": CORPUS / "water_dimer.molden",
}

CASE_METADATA = {
    "water": {"molecular_charge": 0, "open_shell": False},
    "methane": {"molecular_charge": 0, "open_shell": False},
    "ammonia": {"molecular_charge": 0, "open_shell": False},
    "carbon_dioxide": {"molecular_charge": 0, "open_shell": False},
    "benzene": {"molecular_charge": 0, "open_shell": False},
    "ethanol": {"molecular_charge": 0, "open_shell": False},
    "ammonium_cation": {"molecular_charge": 1, "open_shell": False},
    "oxygen_triplet": {"molecular_charge": 0, "open_shell": True},
    "oh_diffuse_uhf": {"molecular_charge": 0, "open_shell": True},
    "water_dimer": {"molecular_charge": 0, "open_shell": False},
}

STANDARD = AtomQuadratureSettings()
FINE = AtomQuadratureSettings(
    radial_points=144,
    theta_points=24,
    phi_points=48,
    radial_extent_bohr=24.0,
    chunk_size=65536,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _trapezoid_weights(radius: np.ndarray) -> np.ndarray:
    """Return nonuniform trapezoid weights for integral f(r) dr."""

    r = np.asarray(radius, dtype=float)
    if r.ndim != 1 or r.size < 2 or np.any(np.diff(r) <= 0.0):
        raise ValueError("Reference radii must be a strictly increasing 1-D array.")
    weights = np.empty_like(r)
    weights[0] = 0.5 * (r[1] - r[0])
    weights[-1] = 0.5 * (r[-1] - r[-2])
    weights[1:-1] = 0.5 * (r[2:] - r[:-2])
    return weights


def _one_rdm_from_iodata(mol: Any) -> np.ndarray:
    """Return spin-summed AO one-RDM from IOData or its parsed MO data."""

    for key in ("post_scf", "scf"):
        matrix = mol.one_rdms.get(key)
        if matrix is not None:
            return np.asarray(matrix, dtype=float)
    mo = mol.mo
    if mo is None or mo.coeffs is None or mo.occs is None:
        raise ValueError("Independent validator requires MO coefficients and occupations.")
    coeffs = np.asarray(mo.coeffs, dtype=float)
    occs = np.asarray(mo.occs, dtype=float)
    if coeffs.ndim != 2 or occs.ndim != 1 or coeffs.shape[1] != occs.size:
        raise ValueError(
            f"Unexpected IOData MO dimensions: coeffs={coeffs.shape}, occs={occs.shape}."
        )
    return (coeffs * occs[None, :]) @ coeffs.T


def _horton_charges(path: Path) -> tuple[np.ndarray, float, dict[str, Any]]:
    """Compute independent Hirshfeld charges with HORTON-PART/qc-grid/GBasis."""

    try:
        from gbasis.evals.eval import evaluate_basis
        from gbasis.wrappers import from_iodata
        from grid import BeckeWeights, ExpRTransform, MolGrid, OneDGrid, UniformInteger
        from horton_part import HirshfeldWPart, ProAtomDB, ProAtomRecord
        from iodata import load_one
    except ImportError as exc:
        raise RuntimeError(
            "Independent validation requires horton-part==1.1.8, scipy<1.17, "
            "and openWFN's interop dependencies."
        ) from exc

    mol = load_one(str(path))
    if mol.obasis is None or mol.mo is None:
        raise ValueError(f"Independent validator could not recover a wavefunction from {path}.")

    transform = ExpRTransform(5.0e-4, 2.0e1, 120 - 1)
    radial_grid = transform.transform_1d_grid(UniformInteger(120))
    grid = MolGrid.from_preset(
        mol.atnums,
        mol.atcoords,
        "fine",
        radial_grid,
        BeckeWeights(),
        rotate=False,
        store=True,
    )

    one_rdm = _one_rdm_from_iodata(mol)
    basis = from_iodata(mol)
    basis_grid = evaluate_basis(basis, grid.points)
    density = np.einsum("ab,bp,ap->p", one_rdm, basis_grid, basis_grid, optimize=True)
    density = np.asarray(density, dtype=float)
    integrated_electrons = float(grid.integrate(density))

    library = load_hirshfeld_reference_library("v1")
    manifest = json.loads(library.manifest_json)
    records = []
    for symbol in library.supported_elements:
        reference = library.for_element(symbol)
        radial_weights = (
            4.0
            * math.pi
            * reference.radius_bohr**2
            * _trapezoid_weights(reference.radius_bohr)
        )
        record = manifest["elements"][symbol]
        records.append(
            ProAtomRecord(
                reference.atomic_number,
                0,
                float(record["scf_energy_hartree"]),
                OneDGrid(reference.radius_bohr.copy(), radial_weights),
                reference.density_e_per_bohr3.copy(),
                pseudo_number=reference.atomic_number,
            )
        )
    database = ProAtomDB(records)
    partition = HirshfeldWPart(
        coordinates=mol.atcoords,
        numbers=mol.atnums,
        pseudo_numbers=mol.atnums,
        grid=grid,
        moldens=density,
        proatomdb=database,
        lmax=3,
        grid_type=3,
    )
    partition.do_charges()
    charges = np.asarray(partition.cache["charges"], dtype=float).copy()
    if charges.shape != np.asarray(mol.atnums).shape or not np.all(np.isfinite(charges)):
        raise RuntimeError("HORTON-PART returned malformed Hirshfeld charges.")

    metadata = {
        "horton_part_version": _package_version("horton-part"),
        "scipy_version": _package_version("scipy"),
        "qc_grid_version": _package_version("qc-grid"),
        "qc_iodata_version": _package_version("qc-iodata"),
        "gbasis_version": _package_version("qc-gbasis") or _package_version("gbasis"),
        "grid_size": int(grid.size),
        "grid_type": 3,
        "density_electrons": integrated_electrons,
        "charge_sum_e": float(np.sum(charges)),
        "mo_kind": mol.mo.kind,
    }
    return charges, integrated_electrons, metadata


def _openwfn_charges(path: Path, grid: AtomQuadratureSettings) -> tuple[np.ndarray, Any]:
    result = load(path).hirshfeld(settings=HirshfeldSettings(quadrature=grid))
    charges = np.asarray([row["charge"] for row in result.data["atoms"]], dtype=float)
    return charges, result


def _grid_dict(grid: AtomQuadratureSettings) -> dict[str, Any]:
    return {
        "radial_points": grid.radial_points,
        "theta_points": grid.theta_points,
        "phi_points": grid.phi_points,
        "radial_extent_bohr": grid.radial_extent_bohr,
        "chunk_size": grid.chunk_size,
    }


def validate_case(name: str, path: Path, external: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    standard_charges, standard = _openwfn_charges(path, STANDARD)
    fine_charges, fine = _openwfn_charges(path, FINE)
    convergence_shift = np.abs(standard_charges - fine_charges)
    metadata = CASE_METADATA[name]

    convergence = {
        "id": name,
        "input_path": str(path.relative_to(ROOT)),
        "input_sha256": _sha256(path),
        "standard_status": standard.status,
        "fine_status": fine.status,
        "standard_charges_e": standard_charges.tolist(),
        "fine_charges_e": fine_charges.tolist(),
        "max_abs_charge_shift_e": float(np.max(convergence_shift)),
        "convergence_gate_passed": bool(
            standard.status == "success"
            and fine.status == "success"
            and float(np.max(convergence_shift)) <= CONVERGENCE_TOLERANCE_E
        ),
    }

    reference: dict[str, Any] = {
        "id": name,
        "input_path": str(path.relative_to(ROOT)),
        "input_sha256": _sha256(path),
        "molecular_charge": metadata["molecular_charge"],
        "open_shell": metadata["open_shell"],
        "ordinary_hirshfeld_uses_total_density": True,
        "openwfn_standard_status": standard.status,
        "openwfn_standard_charges_e": standard_charges.tolist(),
    }
    if external:
        independent, independent_electrons, external_metadata = _horton_charges(path)
        if independent.shape != standard_charges.shape:
            raise RuntimeError(
                f"Charge-vector shape mismatch for {name}: {independent.shape} != {standard_charges.shape}."
            )
        differences = np.abs(standard_charges - independent)
        reference.update(
            {
                "external_tool_version": external_metadata["horton_part_version"],
                "external_metadata": external_metadata,
                "external_density_electrons": independent_electrons,
                "external_charges_e": independent.tolist(),
                "max_abs_external_difference_e": float(np.max(differences)),
                "external_gate_passed": bool(
                    standard.status == "success"
                    and float(np.max(differences)) <= REFERENCE_TOLERANCE_E
                ),
            }
        )
    return reference, convergence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--cases",
        default=",".join(CASES),
        help="Comma-separated case names; defaults to the full validation set.",
    )
    parser.add_argument(
        "--external",
        action="store_true",
        help="Run HORTON-PART independent comparisons in addition to convergence evidence.",
    )
    args = parser.parse_args()

    names = tuple(item.strip() for item in args.cases.split(",") if item.strip())
    unknown = [name for name in names if name not in CASES]
    if unknown:
        parser.error("Unknown Hirshfeld validation case(s): " + ", ".join(unknown))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    library = load_hirshfeld_reference_library("v1")
    references = []
    convergence = []
    for name in names:
        ref, conv = validate_case(name, CASES[name], args.external)
        references.append(ref)
        convergence.append(conv)

    convergence_by_id = {case["id"]: case for case in convergence}
    validated_case_ids = sorted(
        case["id"]
        for case in references
        if args.external
        and case.get("external_gate_passed", False)
        and convergence_by_id[case["id"]]["convergence_gate_passed"]
    )
    full_validation_set = set(names) == set(CASES)
    promotion_status = (
        "Validated"
        if args.external and full_validation_set and set(validated_case_ids) == set(CASES)
        else "Experimental"
    )

    reference_report = {
        "schema_version": "1.0",
        "method": "Hirshfeld",
        "external_reference": {
            "tool": "HORTON-PART",
            "version": _package_version("horton-part") if args.external else None,
            "runtime_dependency": False,
            "integration_mode": "common molecular grid (grid_type=3)",
        },
        "reference_library": {
            "id": library.library_id,
            "sha256": library.library_sha256,
            "version": library.version,
        },
        "acceptance": {
            "max_per_atom_external_difference_e": REFERENCE_TOLERANCE_E,
        },
        "standard_settings": _grid_dict(STANDARD),
        "python_version": platform.python_version(),
        "validated_case_ids": validated_case_ids,
        "promotion_status": promotion_status,
        "cases": references,
    }
    convergence_report = {
        "schema_version": "1.0",
        "method": "Hirshfeld",
        "acceptance": {
            "max_per_atom_grid_shift_e": CONVERGENCE_TOLERANCE_E,
        },
        "standard_settings": _grid_dict(STANDARD),
        "fine_settings": _grid_dict(FINE),
        "validated_case_ids": validated_case_ids,
        "cases": convergence,
    }
    (args.output_dir / "reference-report.json").write_text(
        json.dumps(reference_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output_dir / "convergence-report.json").write_text(
        json.dumps(convergence_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    reference_failures = [
        case["id"] for case in references if args.external and not case["external_gate_passed"]
    ]
    convergence_failures = [
        case["id"] for case in convergence if not case["convergence_gate_passed"]
    ]
    print(f"Reference cases: {len(references)}; failures: {reference_failures}")
    print(f"Convergence cases: {len(convergence)}; failures: {convergence_failures}")
    print(f"Promotion status: {promotion_status}; validated cases: {len(validated_case_ids)}")
    return 1 if reference_failures or convergence_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
