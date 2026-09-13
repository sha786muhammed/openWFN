from dataclasses import FrozenInstanceError

import pytest

from openwfn.errors import (
    DataUnavailableError,
    ExternalProgramError,
    ParseError,
    ValidationError,
)
from openwfn.model import (
    MODEL_SCHEMA_VERSION,
    Atom,
    BasisSet,
    BasisShell,
    BoundaryConditions,
    CalculationMetadata,
    DensityMatrix,
    MolecularOrbitals,
    Molecule,
    Provenance,
    VolumetricGrid,
)


def test_atom_is_immutable_and_declares_coordinate_units() -> None:
    atom = Atom(atomic_number=8, coordinates=(0.0, 0.0, 0.114049))

    assert atom.coordinate_unit == "angstrom"
    with pytest.raises(FrozenInstanceError):
        atom.atomic_number = 1  # type: ignore[misc]


def test_atom_rejects_invalid_atomic_number() -> None:
    with pytest.raises(ValueError, match="atomic number"):
        Atom(atomic_number=0, coordinates=(0.0, 0.0, 0.0))


def test_molecule_rejects_nonpositive_multiplicity() -> None:
    metadata = CalculationMetadata(source_program="Gaussian")

    with pytest.raises(ValueError, match="multiplicity"):
        Molecule(
            atoms=(Atom(1, (0.0, 0.0, 0.0)),),
            charge=0,
            multiplicity=0,
            metadata=metadata,
        )


def test_molecule_defaults_to_isolated_boundary_conditions() -> None:
    molecule = Molecule(
        atoms=(Atom(1, (0.0, 0.0, 0.0)),),
        charge=0,
        multiplicity=1,
        metadata=CalculationMetadata("fixture"),
    )

    assert MODEL_SCHEMA_VERSION == "2.0"
    assert molecule.boundary_conditions == BoundaryConditions()
    assert molecule.boundary_conditions.kind == "isolated"


def test_v2_foundation_rejects_periodic_boundary_conditions() -> None:
    with pytest.raises(ValueError, match="periodic boundary conditions are not supported"):
        BoundaryConditions(kind="periodic")  # type: ignore[arg-type]


def test_orbitals_reject_coefficient_shape_mismatch() -> None:
    with pytest.raises(ValueError, match="coefficient matrix"):
        MolecularOrbitals(
            energies=(-0.5, 0.2),
            coefficients=((1.0,),),
            occupations=(2.0, 0.0),
        )


def test_density_matrix_rejects_nonsquare_values() -> None:
    with pytest.raises(ValueError, match="square"):
        DensityMatrix(values=((1.0, 0.0),), kind="total")


def test_basis_shell_requires_matching_primitive_arrays() -> None:
    with pytest.raises(ValueError, match="primitive"):
        BasisShell(
            atom_index=0,
            angular_momentum=0,
            exponents=(1.0, 0.5),
            coefficients=(1.0,),
        )


def test_basis_set_counts_functions_from_shells() -> None:
    basis = BasisSet(
        shells=(
            BasisShell(0, 0, (1.0,), (1.0,)),
            BasisShell(0, 1, (0.5,), (1.0,)),
        )
    )

    assert basis.n_functions == 4


def test_grid_rejects_value_count_different_from_shape() -> None:
    with pytest.raises(ValueError, match="grid values"):
        VolumetricGrid(
            origin=(0.0, 0.0, 0.0),
            axes=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
            shape=(2, 2, 2),
            values=(0.0,),
            value_unit="electron/bohr^3",
        )


def test_provenance_requires_sha256_checksum() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        Provenance(source_path="water.fchk", sha256="abc", parser="gaussian-fchk")


def test_v07_metadata_constructor_remains_compatible() -> None:
    metadata = CalculationMetadata("Gaussian", "# RHF/3-21G", "RHF", "3-21G")

    assert metadata.route == "# RHF/3-21G"
    assert metadata.source_program_version is None


def test_provenance_exposes_versioned_ingestion_metadata() -> None:
    provenance = Provenance(
        source_path="water.fchk",
        sha256="a" * 64,
        parser="gaussian-fchk",
        source_format="fchk",
        parser_version="1",
        transformations=("bohr-to-angstrom",),
    )

    assert provenance.source_format == "fchk"
    assert provenance.parser_version == "1"
    assert provenance.transformations == ("bohr-to-angstrom",)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("source_format", "", "source format"),
        ("parser_version", "", "parser version"),
    ],
)
def test_provenance_rejects_blank_ingestion_metadata(
    field: str, value: str, message: str
) -> None:
    arguments = {
        "source_path": "water.fchk",
        "sha256": "a" * 64,
        "parser": "gaussian-fchk",
        "source_format": "fchk",
        "parser_version": "1",
    }
    arguments[field] = value

    with pytest.raises(ValueError, match=message):
        Provenance(**arguments)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("error_type", "expected_code"),
    [
        (ParseError, 3),
        (DataUnavailableError, 4),
        (ValidationError, 5),
        (ExternalProgramError, 6),
    ],
)
def test_domain_errors_have_stable_exit_codes(error_type, expected_code: int) -> None:
    assert error_type("failure").exit_code == expected_code
