"""Independent PySCF field comparisons for Experimental ELF and LOL.

These tests regenerate small SCF wavefunctions with PySCF, serialize them through
PySCF's Molden writer, load the resulting wavefunction through openWFN, and then
compare openWFN localization results with density, density-gradient, and positive-
definite KED fields reconstructed directly from PySCF AO derivatives and density
matrices.  The reference formulas below intentionally do not call openWFN
localization kernels.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from openwfn.api import load

CASES = (
    (
        "water",
        "O 0 0 0; H 0 -.757 .587; H 0 .757 .587",
        "sto-3g",
        0,
        0,
        False,
        ("total",),
    ),
    (
        "water_cartesian",
        "O 0 0 0; H 0 -.757 .587; H 0 .757 .587",
        "6-31g*",
        0,
        0,
        True,
        ("total",),
    ),
    (
        "ammonium_cation",
        "N 0 0 0; H .59 .59 .59; H -.59 -.59 .59; H -.59 .59 -.59; H .59 -.59 -.59",
        "6-31g*",
        0,
        1,
        False,
        ("total",),
    ),
    (
        "oh_diffuse_uhf",
        "O 0 0 0; H 0 0 .97",
        "6-31+g*",
        1,
        0,
        False,
        ("alpha", "beta"),
    ),
    (
        "oxygen_triplet",
        "O 0 0 -.605; O 0 0 .605",
        "6-31g*",
        2,
        0,
        False,
        ("alpha", "beta"),
    ),
)

OFFSETS_BOHR = np.array(
    (
        (0.21, 0.37, 0.29),
        (-0.41, 0.25, 0.33),
        (0.55, -0.31, 0.47),
        (0.19, -0.49, -0.27),
    ),
    dtype=float,
)


def _reference_fields(mol, mean_field, points_bohr: np.ndarray, channel: str):
    from pyscf.dft import numint

    ao = np.asarray(numint.eval_ao(mol, points_bohr, deriv=1), dtype=float)
    values = ao[0]
    gradients = ao[1:4]
    density_matrix = np.asarray(mean_field.make_rdm1(), dtype=float)

    if channel == "total":
        assert density_matrix.ndim == 2
        dm = density_matrix
        spin_resolved = False
    else:
        assert density_matrix.ndim == 3 and density_matrix.shape[0] == 2
        dm = density_matrix[0 if channel == "alpha" else 1]
        spin_resolved = True

    rho = np.einsum("pi,ij,pj->p", values, dm, values, optimize=True)
    gradient = 2.0 * np.einsum(
        "xpi,ij,pj->px", gradients, dm, values, optimize=True
    )
    tau = 0.5 * sum(
        np.einsum("pi,ij,pj->p", component, dm, component, optimize=True)
        for component in gradients
    )

    coefficient = (
        (3.0 / 10.0) * (6.0 * np.pi**2) ** (2.0 / 3.0)
        if spin_resolved
        else (3.0 / 10.0) * (3.0 * np.pi**2) ** (2.0 / 3.0)
    )
    reference_ked = coefficient * np.power(rho, 5.0 / 3.0)
    gradient_squared = np.einsum("pi,pi->p", gradient, gradient, optimize=True)
    von_weizsaecker = gradient_squared / (8.0 * rho)
    pauli_excess = tau - von_weizsaecker
    elf = np.square(reference_ked) / (
        np.square(reference_ked) + np.square(pauli_excess)
    )
    lol = reference_ked / (reference_ked + tau)
    return rho, tau, reference_ked, elf, lol


@pytest.mark.parametrize(
    ("name", "geometry", "basis", "spin", "charge", "cartesian", "channels"),
    CASES,
    ids=[case[0] for case in CASES],
)
def test_localization_matches_independent_pyscf_fields(
    name: str,
    geometry: str,
    basis: str,
    spin: int,
    charge: int,
    cartesian: bool,
    channels: tuple[str, ...],
    tmp_path: Path,
) -> None:
    pytest.importorskip("iodata")
    pytest.importorskip("pyscf")
    from pyscf import gto, lib, scf
    from pyscf.tools import molden

    lib.num_threads(1)
    molecule = gto.M(
        atom=geometry,
        basis=basis,
        spin=spin,
        charge=charge,
        cart=cartesian,
        verbose=0,
    )
    molecule.incore_anyway = True
    mean_field = scf.UHF(molecule) if spin else scf.RHF(molecule)
    mean_field.conv_tol = 1.0e-11
    mean_field.kernel()
    assert mean_field.converged, name

    source = tmp_path / f"{name}.molden"
    molden.from_scf(mean_field, str(source))
    calculation = load(source)
    points = molecule.atom_coords()[0] + OFFSETS_BOHR

    for channel in channels:
        rho, tau, reference_ked, reference_elf, reference_lol = _reference_fields(
            molecule, mean_field, points, channel
        )
        assert np.all(rho > 1.0e-8), (name, channel, rho)

        elf = calculation.analyze(
            "elf", points_bohr=points, channel=channel, chunk_size=2
        )
        lol = calculation.analyze(
            "lol", points_bohr=points, channel=channel, chunk_size=2
        )

        assert elf.status == "success", (name, channel, elf.error, elf.warnings)
        assert lol.status == "success", (name, channel, lol.error, lol.warnings)
        assert elf.validation_status == "Experimental"
        assert lol.validation_status == "Experimental"

        np.testing.assert_allclose(
            np.asarray(elf.data["rho"], dtype=float), rho, rtol=3.0e-7, atol=3.0e-9
        )
        np.testing.assert_allclose(
            np.asarray(elf.data["tau"], dtype=float), tau, rtol=2.0e-6, atol=2.0e-8
        )
        np.testing.assert_allclose(
            np.asarray(elf.data["reference_ked"], dtype=float),
            reference_ked,
            rtol=7.0e-7,
            atol=5.0e-9,
        )
        np.testing.assert_allclose(
            np.asarray(elf.data["values"], dtype=float),
            reference_elf,
            rtol=5.0e-6,
            atol=5.0e-8,
        )
        np.testing.assert_allclose(
            np.asarray(lol.data["values"], dtype=float),
            reference_lol,
            rtol=5.0e-6,
            atol=5.0e-8,
        )

        assert elf.data["conventions"]["kinetic_energy_density"] == (
            "positive_definite_half_gradient_square"
        )
        assert lol.data["conventions"]["kinetic_energy_density"] == (
            "positive_definite_half_gradient_square"
        )
