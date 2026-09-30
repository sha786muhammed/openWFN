"""IOData 1.0.1 adapter into openWFN-owned canonical types.

The optional backend is imported lazily inside :func:`load_iodata`.  No IOData
class is part of the public openWFN model or result contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from math import isclose, sqrt
from pathlib import Path
from typing import Any

import numpy as np

from ..analysis.basis import _cartesian_powers, _primitive_overlap
from ..constants import BOHR_TO_ANGSTROM
from ..data import (
    IntegralData,
    IntegralTerm,
    OpenWFNData,
    PeriodicData,
    SourceMetadata,
    StructureData,
)
from ..errors import ParseError
from ..model import (
    Atom,
    BasisSet,
    BasisShell,
    Bond,
    CalculationData,
    CalculationMetadata,
    DensityMatrix,
    MolecularOrbitals,
    Molecule,
    Provenance,
    VolumetricGrid,
)


@dataclass(frozen=True, slots=True)
class BackendProvenance(Provenance):
    """Provenance enriched with the optional parser backend identity."""

    backend: str | None = None
    backend_version: str | None = None

    def __post_init__(self) -> None:
        super(BackendProvenance, self).__post_init__()
        if self.backend is not None and not self.backend.strip():
            raise ValueError("backend must not be blank")
        if self.backend_version is not None and not self.backend_version.strip():
            raise ValueError("backend_version must not be blank")


_PROGRAM_BY_FORMAT = {
    "cp2klog": "CP2K",
    "gamess": "GAMESS",
    "gaussianinput": "Gaussian",
    "gaussianlog": "Gaussian",
    "orcalog": "ORCA",
    "qchemlog": "Q-Chem",
}


def _safe_attr(obj: Any, name: str) -> Any:
    try:
        return getattr(obj, name, None)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return None


def _as_float_array(value: Any) -> np.ndarray | None:
    if value is None:
        return None
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return None
    if array.size == 0 or not np.all(np.isfinite(array)):
        return None
    return array


def _integer_like(value: Any) -> int | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    rounded = round(number)
    return int(rounded) if isclose(number, rounded, abs_tol=1e-8) else None


def _source_metadata(loaded: Any, format_id: str) -> SourceMetadata:
    energy = _safe_attr(loaded, "energy")
    try:
        energy_value = float(energy) if energy is not None else None
    except (TypeError, ValueError):
        energy_value = None
    if energy_value is not None and not np.isfinite(energy_value):
        energy_value = None
    title = _safe_attr(loaded, "title")
    return SourceMetadata(
        source_program=_PROGRAM_BY_FORMAT.get(format_id),
        title=str(title) if title else None,
        energy_hartree=energy_value,
    )


def _structure_from_loaded(loaded: Any, warnings: list[str]) -> StructureData | None:
    coordinates = _as_float_array(_safe_attr(loaded, "atcoords"))
    if coordinates is None:
        return None
    if coordinates.ndim != 2 or coordinates.shape[1] != 3:
        warnings.append("IOData atom coordinates had an unsupported shape; structure was withheld.")
        return None

    atnums = _safe_attr(loaded, "atnums")
    if atnums is None:
        atomic_numbers: tuple[int | None, ...] = (None,) * coordinates.shape[0]
    else:
        try:
            values = np.asarray(atnums).reshape(-1)
            if len(values) != coordinates.shape[0]:
                raise ValueError
            integer_numbers = tuple(_integer_like(value) for value in values)
            if any(number is None for number in integer_numbers):
                raise ValueError
            atomic_numbers = tuple(
                number if number > 0 else None for number in integer_numbers
            )
        except (TypeError, ValueError, OverflowError):
            warnings.append("IOData atomic numbers were inconsistent with coordinates; they were withheld.")
            atomic_numbers = (None,) * coordinates.shape[0]

    bonds: list[Bond] = []
    raw_bonds = _safe_attr(loaded, "bonds")
    if raw_bonds is not None:
        try:
            bond_array = np.asarray(raw_bonds)
            if bond_array.ndim == 2 and bond_array.shape[1] >= 2:
                for row in bond_array:
                    atom1, atom2 = int(row[0]), int(row[1])
                    order = 1
                    if len(row) >= 3:
                        candidate = _integer_like(row[2])
                        if candidate is not None and candidate >= 1:
                            order = candidate
                    if atom1 != atom2 and 0 <= atom1 < len(atomic_numbers) and 0 <= atom2 < len(atomic_numbers):
                        bonds.append(Bond(atom1, atom2, order))
        except (TypeError, ValueError, OverflowError):
            warnings.append("IOData bond data could not be represented safely and was omitted.")

    charge = _integer_like(_safe_attr(loaded, "charge"))
    spinpol = _integer_like(_safe_attr(loaded, "spinpol"))
    multiplicity = abs(spinpol) + 1 if spinpol is not None else None
    converted = tuple(
        tuple(float(component) * BOHR_TO_ANGSTROM for component in row)
        for row in coordinates
    )
    return StructureData(
        coordinates=converted,
        atomic_numbers=atomic_numbers,
        bonds=tuple(bonds),
        charge=charge,
        multiplicity=multiplicity,
    )


def _periodic_from_loaded(loaded: Any, warnings: list[str]) -> PeriodicData | None:
    cell = _as_float_array(_safe_attr(loaded, "cellvecs"))
    if cell is None:
        return None
    if cell.shape != (3, 3):
        warnings.append(
            "IOData periodic cell does not contain exactly three vectors; periodic data was withheld."
        )
        return None
    vectors = tuple(
        tuple(float(component) * BOHR_TO_ANGSTROM for component in row)
        for row in cell
    )
    return PeriodicData(cell_vectors=vectors)  # type: ignore[arg-type]


def _grid_from_loaded(loaded: Any, warnings: list[str]) -> tuple[VolumetricGrid, ...]:
    cube = _safe_attr(loaded, "cube")
    if cube is None:
        return ()
    origin = _as_float_array(_safe_attr(cube, "origin"))
    axes = _as_float_array(_safe_attr(cube, "axes"))
    values = _as_float_array(_safe_attr(cube, "data"))
    if origin is None or axes is None or values is None or origin.shape != (3,) or axes.shape != (3, 3):
        warnings.append("IOData volumetric grid was incomplete or malformed and was withheld.")
        return ()
    shape = tuple(int(item) for item in values.shape)
    if len(shape) != 3:
        warnings.append("IOData volumetric grid was not three-dimensional and was withheld.")
        return ()
    return (
        VolumetricGrid(
            origin=tuple(float(value) * BOHR_TO_ANGSTROM for value in origin),  # type: ignore[arg-type]
            axes=tuple(
                tuple(float(value) * BOHR_TO_ANGSTROM for value in row) for row in axes
            ),  # type: ignore[arg-type]
            shape=shape,  # type: ignore[arg-type]
            values=tuple(float(value) for value in values.ravel()),
            value_unit="atomic-unit",
        ),
    )


def _sparse_terms(array: np.ndarray, rank: int) -> tuple[IntegralTerm, ...]:
    if array.ndim != rank:
        raise ValueError(f"expected a rank-{rank} integral tensor")
    terms: list[IntegralTerm] = []
    for index, value in np.ndenumerate(array):
        numeric = float(value)
        if numeric != 0.0:
            terms.append(IntegralTerm(tuple(int(item) for item in index), numeric))
    return tuple(terms)


def _integrals_from_loaded(loaded: Any, warnings: list[str]) -> IntegralData | None:
    one_map = _safe_attr(loaded, "one_ints")
    two_map = _safe_attr(loaded, "two_ints")
    one = None
    two = None
    if isinstance(one_map, dict):
        omitted = sorted(str(key) for key in one_map if key != "core_mo")
        if omitted:
            warnings.append(
                "IOData one-electron integral fields not represented by openWFN were omitted: "
                + ", ".join(omitted) + "."
            )
        one = _as_float_array(one_map.get("core_mo"))
    if isinstance(two_map, dict):
        omitted = sorted(str(key) for key in two_map if key != "two_mo")
        if omitted:
            warnings.append(
                "IOData two-electron integral fields not represented by openWFN were omitted: "
                + ", ".join(omitted) + "."
            )
        two = _as_float_array(two_map.get("two_mo"))

    core_energy = _safe_attr(loaded, "core_energy")
    try:
        core = float(core_energy) if core_energy is not None else None
    except (TypeError, ValueError):
        core = None
    if core is not None and not np.isfinite(core):
        core = None

    n_electrons = _integer_like(_safe_attr(loaded, "nelec"))
    if one is None and two is None and core is None:
        return None

    n_orbitals: int | None = None
    try:
        if one is not None:
            if one.ndim != 2 or one.shape[0] != one.shape[1]:
                raise ValueError("one-electron integral matrix must be square")
            n_orbitals = int(one.shape[0])
        if two is not None:
            if two.ndim != 4 or len(set(two.shape)) != 1:
                raise ValueError("two-electron integral tensor must be square in all dimensions")
            if n_orbitals is not None and two.shape[0] != n_orbitals:
                raise ValueError("one- and two-electron integral dimensions disagree")
            n_orbitals = int(two.shape[0])
        return IntegralData(
            n_orbitals=n_orbitals,
            n_electrons=n_electrons,
            core_energy_hartree=core,
            one_electron=_sparse_terms(one, 2) if one is not None else (),
            two_electron=_sparse_terms(two, 4) if two is not None else (),
        )
    except ValueError as exc:
        warnings.append(f"IOData integral data was withheld: {exc}")
        return None


def _cartesian_names(angular_momentum: int) -> tuple[str, ...]:
    powers = _cartesian_powers(angular_momentum)
    names = []
    for nx, ny, nz in powers:
        name = "x" * nx + "y" * ny + "z" * nz
        names.append(name or "1")
    return tuple(names)


def _pure_names(angular_momentum: int) -> tuple[str, ...]:
    names = ["c0"]
    for magnetic in range(1, angular_momentum + 1):
        names.extend((f"c{magnetic}", f"s{magnetic}"))
    return tuple(names)


def _expected_convention(angular_momentum: int, kind: str) -> tuple[str, ...]:
    if kind == "c":
        return _cartesian_names(angular_momentum)
    if kind == "p" and angular_momentum >= 2:
        return _pure_names(angular_momentum)
    raise ValueError(f"unsupported IOData basis kind '{kind}' for l={angular_momentum}")


def _basis_and_scales(loaded: Any) -> tuple[BasisSet, np.ndarray]:
    obasis = _safe_attr(loaded, "obasis")
    if obasis is None:
        raise ValueError("orbital basis is missing")
    if str(_safe_attr(obasis, "primitive_normalization")) != "L2":
        raise ValueError("only IOData L2-normalized orbital primitives are supported")
    conventions = _safe_attr(obasis, "conventions")
    if not isinstance(conventions, dict):
        raise ValueError("IOData basis conventions are missing")

    shells: list[BasisShell] = []
    ao_scales: list[float] = []
    for shell in _safe_attr(obasis, "shells") or ():
        exponents = np.asarray(_safe_attr(shell, "exponents"), dtype=float).reshape(-1)
        coeffs = np.asarray(_safe_attr(shell, "coeffs"), dtype=float)
        angmoms = np.asarray(_safe_attr(shell, "angmoms"), dtype=int).reshape(-1)
        raw_kinds = _safe_attr(shell, "kinds")
        kinds = tuple(str(item) for item in raw_kinds) if raw_kinds is not None else ()
        if coeffs.ndim == 1:
            coeffs = coeffs.reshape(-1, 1)
        if coeffs.shape != (len(exponents), len(angmoms)) or len(kinds) != len(angmoms):
            raise ValueError("IOData generalized-contraction dimensions are inconsistent")
        if np.any(exponents <= 0.0) or not np.all(np.isfinite(coeffs)):
            raise ValueError("IOData basis contains invalid exponents or coefficients")

        for column, (angular_momentum, kind) in enumerate(zip(angmoms, kinds, strict=True)):
            angular = int(angular_momentum)
            kind = kind.lower()
            expected = _expected_convention(angular, kind)
            actual = tuple(str(item) for item in conventions.get((angular, kind), ()))
            if actual != expected:
                raise ValueError(
                    f"basis convention {actual!r} for l={angular}/{kind} is not yet mapped to openWFN order {expected!r}"
                )
            contraction = coeffs[:, column]
            powers = (angular, 0, 0)
            overlap = np.asarray(
                [
                    [_primitive_overlap(float(a), float(b), powers) for b in exponents]
                    for a in exponents
                ],
                dtype=float,
            )
            norm_squared = float(contraction @ overlap @ contraction)
            if not np.isfinite(norm_squared) or norm_squared <= 0.0:
                raise ValueError("IOData contraction normalization is not positive")
            norm = sqrt(norm_squared)
            converted = BasisShell(
                atom_index=int(_safe_attr(shell, "icenter")),
                angular_momentum=angular,
                exponents=tuple(float(value) for value in exponents),
                coefficients=tuple(float(value) for value in contraction),
                pure=kind == "p",
            )
            shells.append(converted)
            ao_scales.extend([norm] * converted.n_functions)

    basis = BasisSet(tuple(shells), name=_safe_attr(loaded, "obasis_name"))
    if not basis.shells or len(ao_scales) != basis.n_functions:
        raise ValueError("IOData basis did not produce a consistent openWFN basis")
    return basis, np.asarray(ao_scales, dtype=float)


def _channel(
    energies: Any,
    coefficients: Any,
    occupations: Any,
    spin: str,
    ao_scales: np.ndarray,
) -> MolecularOrbitals:
    energy_array = np.asarray(energies, dtype=float).reshape(-1)
    coefficient_array = np.asarray(coefficients, dtype=float)
    occupation_array = np.asarray(occupations, dtype=float).reshape(-1)
    if coefficient_array.ndim != 2 or coefficient_array.shape != (
        len(ao_scales),
        len(energy_array),
    ):
        raise ValueError("IOData MO coefficient dimensions do not match the normalized basis")
    if len(occupation_array) != len(energy_array):
        raise ValueError("IOData orbital occupations do not match orbital energies")
    coefficient_array = coefficient_array * ao_scales[:, None]
    return MolecularOrbitals(
        energies=tuple(float(value) for value in energy_array),
        coefficients=tuple(tuple(float(value) for value in row) for row in coefficient_array),
        occupations=tuple(float(value) for value in occupation_array),
        spin=spin,  # type: ignore[arg-type]
        occupation_source="iodata",
    )


def _orbitals_from_loaded(
    loaded: Any, basis: BasisSet, ao_scales: np.ndarray
) -> tuple[MolecularOrbitals, MolecularOrbitals | None]:
    mo = _safe_attr(loaded, "mo")
    if mo is None:
        raise ValueError("molecular orbitals are missing")
    kind = str(_safe_attr(mo, "kind") or "").lower()
    if kind == "restricted":
        occsa = np.asarray(_safe_attr(mo, "occsa"), dtype=float).reshape(-1)
        occsb = np.asarray(_safe_attr(mo, "occsb"), dtype=float).reshape(-1)
        if occsa.shape != occsb.shape:
            raise ValueError("restricted alpha/beta occupation arrays disagree")
        alpha = _channel(
            _safe_attr(mo, "energiesa"),
            _safe_attr(mo, "coeffsa"),
            occsa + occsb,
            "restricted",
            ao_scales,
        )
        return alpha, None
    if kind == "unrestricted":
        alpha = _channel(
            _safe_attr(mo, "energiesa"),
            _safe_attr(mo, "coeffsa"),
            _safe_attr(mo, "occsa"),
            "alpha",
            ao_scales,
        )
        beta = _channel(
            _safe_attr(mo, "energiesb"),
            _safe_attr(mo, "coeffsb"),
            _safe_attr(mo, "occsb"),
            "beta",
            ao_scales,
        )
        return alpha, beta
    raise ValueError(f"IOData orbital kind '{kind or 'unknown'}' is not safely representable")


def _density_from_orbitals(
    alpha: MolecularOrbitals, beta: MolecularOrbitals | None
) -> tuple[DensityMatrix, DensityMatrix | None]:
    ca = np.asarray(alpha.coefficients, dtype=float)
    oa = np.asarray(alpha.occupations, dtype=float)
    pa = (ca * oa[None, :]) @ ca.T
    if beta is None:
        return (
            DensityMatrix(tuple(tuple(float(v) for v in row) for row in pa), "total", source="iodata-orbitals"),
            None,
        )
    cb = np.asarray(beta.coefficients, dtype=float)
    ob = np.asarray(beta.occupations, dtype=float)
    pb = (cb * ob[None, :]) @ cb.T
    total = pa + pb
    spin = pa - pb
    return (
        DensityMatrix(tuple(tuple(float(v) for v in row) for row in total), "total", source="iodata-orbitals"),
        DensityMatrix(tuple(tuple(float(v) for v in row) for row in spin), "spin", source="iodata-orbitals"),
    )


def _charge_and_multiplicity(loaded: Any, mo: Any, transformations: list[str]) -> tuple[int | None, int | None]:
    charge = _integer_like(_safe_attr(loaded, "charge"))
    spinpol = _integer_like(_safe_attr(loaded, "spinpol"))
    if spinpol is None and mo is not None:
        occsa = _as_float_array(_safe_attr(mo, "occsa"))
        occsb = _as_float_array(_safe_attr(mo, "occsb"))
        if occsa is not None and occsb is not None:
            spinpol = _integer_like(float(np.sum(occsa) - np.sum(occsb)))
            if spinpol is not None:
                transformations.append("multiplicity derived from IOData alpha/beta occupations")
    multiplicity = abs(spinpol) + 1 if spinpol is not None else None
    return charge, multiplicity


def _calculation_from_loaded(
    loaded: Any,
    structure: StructureData | None,
    periodic: PeriodicData | None,
    metadata: SourceMetadata,
    provenance: BackendProvenance,
    warnings: list[str],
    transformations: list[str],
) -> CalculationData | None:
    obasis = _safe_attr(loaded, "obasis")
    mo = _safe_attr(loaded, "mo")
    if obasis is None and mo is None:
        return None
    if obasis is None or mo is None:
        warnings.append(
            "IOData source exposes incomplete wavefunction data; openWFN withheld CalculationData."
        )
        return None
    if structure is None or periodic is not None or any(number is None for number in structure.atomic_numbers):
        warnings.append(
            "IOData wavefunction could not be attached to a complete isolated molecular structure; openWFN withheld CalculationData."
        )
        return None

    try:
        basis, ao_scales = _basis_and_scales(loaded)
        alpha, beta = _orbitals_from_loaded(loaded, basis, ao_scales)
        charge, multiplicity = _charge_and_multiplicity(loaded, mo, transformations)
        if charge is None or multiplicity is None:
            raise ValueError("charge or multiplicity is not unambiguously available")
        core_numbers = _as_float_array(_safe_attr(loaded, "atcorenums"))
        if core_numbers is not None and len(core_numbers.reshape(-1)) != len(structure.atomic_numbers):
            core_numbers = None
            warnings.append("IOData effective core charges were inconsistent with the atom count and were omitted.")
        core_flat = core_numbers.reshape(-1) if core_numbers is not None else None
        atoms = tuple(
            Atom(
                atomic_number=int(number),
                coordinates=coordinates,
                nuclear_charge=float(core_flat[index]) if core_flat is not None else None,
            )
            for index, (number, coordinates) in enumerate(
                zip(structure.atomic_numbers, structure.coordinates, strict=True)
            )
        )
        calculation_metadata = CalculationMetadata(
            source_program=metadata.source_program or "IOData",
            source_program_version=metadata.source_program_version,
            energy_hartree=metadata.energy_hartree,
        )
        molecule = Molecule(
            atoms=atoms,
            charge=charge,
            multiplicity=multiplicity,
            metadata=calculation_metadata,
            provenance=provenance,
            bonds=structure.bonds,
        )
        total_density, spin_density = _density_from_orbitals(alpha, beta)
        if not np.allclose(ao_scales, 1.0, atol=1e-12, rtol=0.0):
            transformations.append(
                "MO coefficients rescaled for openWFN contraction normalization"
            )
        if alpha.spin == "restricted":
            transformations.append(
                "restricted alpha/beta occupations combined into spin-summed openWFN occupations"
            )
        return CalculationData(
            molecule=molecule,
            basis=basis,
            alpha_orbitals=alpha,
            beta_orbitals=beta,
            total_density=total_density,
            spin_density=spin_density,
        )
    except (TypeError, ValueError) as exc:
        warnings.append(f"IOData wavefunction was withheld: {exc}")
        return None


def _omission_warnings(loaded: Any) -> list[str]:
    omitted: list[str] = []
    for name in ("atgradient", "athessian", "atcharges", "atffparams", "extcharges", "g_rot", "moments"):
        value = _safe_attr(loaded, name)
        if value is not None:
            try:
                present = np.asarray(value).size > 0
            except (TypeError, ValueError):
                present = True
            if present:
                omitted.append(name)
    if not omitted:
        return []
    return [
        "IOData fields not yet represented by OpenWFNData were omitted: " + ", ".join(sorted(omitted)) + "."
    ]


def adapt_iodata_object(
    loaded: Any,
    path: Path,
    *,
    format_id: str,
    backend_version: str,
) -> OpenWFNData:
    """Convert one already-loaded IOData record into openWFN-owned types."""

    source = Path(path)
    raw = source.read_bytes()
    warnings: list[str] = []
    transformations: list[str] = []

    structure = _structure_from_loaded(loaded, warnings)
    if structure is not None:
        transformations.append("coordinates converted bohr -> angstrom")
    periodic = _periodic_from_loaded(loaded, warnings)
    if periodic is not None:
        transformations.append("cell vectors converted bohr -> angstrom")
    grids = _grid_from_loaded(loaded, warnings)
    if grids:
        transformations.append("volumetric grid coordinates converted bohr -> angstrom")
    integrals = _integrals_from_loaded(loaded, warnings)
    if integrals is not None and (integrals.one_electron or integrals.two_electron):
        transformations.append(
            "IOData molecular-orbital integrals converted to zero-based sparse openWFN terms"
        )

    metadata = _source_metadata(loaded, format_id)
    warnings.extend(_omission_warnings(loaded))
    provenance = BackendProvenance(
        source_path=str(source),
        sha256=sha256(raw).hexdigest(),
        parser="openwfn-iodata-adapter",
        warnings=(),
        source_format=format_id,
        parser_version="1",
        transformations=(),
        backend="iodata",
        backend_version=backend_version,
    )
    calculation = _calculation_from_loaded(
        loaded,
        structure,
        periodic,
        metadata,
        provenance,
        warnings,
        transformations,
    )
    final_provenance = BackendProvenance(
        source_path=provenance.source_path,
        sha256=provenance.sha256,
        parser=provenance.parser,
        warnings=tuple(dict.fromkeys(warnings)),
        source_format=provenance.source_format,
        parser_version=provenance.parser_version,
        transformations=tuple(dict.fromkeys(transformations)),
        backend=provenance.backend,
        backend_version=provenance.backend_version,
    )
    if calculation is not None:
        molecule = calculation.molecule
        calculation = CalculationData(
            molecule=Molecule(
                atoms=molecule.atoms,
                charge=molecule.charge,
                multiplicity=molecule.multiplicity,
                metadata=molecule.metadata,
                provenance=final_provenance,
                bonds=molecule.bonds,
                boundary_conditions=molecule.boundary_conditions,
            ),
            basis=calculation.basis,
            alpha_orbitals=calculation.alpha_orbitals,
            beta_orbitals=calculation.beta_orbitals,
            total_density=calculation.total_density,
            spin_density=calculation.spin_density,
            records=calculation.records,
        )
    return OpenWFNData(
        calculation=calculation,
        structure=structure,
        periodic=periodic,
        grids=grids,
        integrals=integrals,
        metadata=metadata,
        provenance=final_provenance,
    )


def load_iodata(path: Path, *, format_id: str) -> OpenWFNData:
    """Load one source with the optional IOData backend and normalize it."""

    try:
        from iodata import load_one
    except ModuleNotFoundError as exc:  # normally normalized by openwfn.ingest
        raise ParseError(
            'IOData is not installed; install the optional backend with pip install "openwfn[interop]".'
        ) from exc
    try:
        backend_version = version("qc-iodata")
    except PackageNotFoundError:
        backend_version = "unknown"
    try:
        loaded = load_one(str(path), fmt=format_id)
    except Exception as exc:
        raise ParseError(f"IOData could not parse {path} as {format_id}: {exc}") from exc
    return adapt_iodata_object(
        loaded,
        Path(path),
        format_id=format_id,
        backend_version=backend_version,
    )
