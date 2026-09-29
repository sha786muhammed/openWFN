#!/usr/bin/env python3
"""Rebuild openWFN-owned interoperability fixtures from local example data.

The quantum-chemical source is the already-distributed examples/water/water.fchk.
Small structure/grid/integral examples are written from format specifications.
No IOData upstream test fixture is copied into this repository.
"""

from __future__ import annotations

import json
import shutil
from hashlib import sha256
from pathlib import Path

import iodata
from iodata.utils import angstrom

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "interop"
ANALYSES = ("beta-frontier", "frontier", "frontier-all", "lowdin", "mulliken", "summary")
CAPABILITIES = (
    "structure", "molecular_metadata", "isolated_molecule", "periodic_cell",
    "basis", "alpha_orbitals", "beta_orbitals", "orbital_occupations",
    "total_density", "spin_density", "ao_overlap", "volumetric_grid",
    "electronic_energy", "integrals",
)
WAVEFUNCTION = {
    "structure", "molecular_metadata", "isolated_molecule", "basis",
    "alpha_orbitals", "orbital_occupations", "total_density", "ao_overlap",
}
MOLECULAR_ANALYSES = {"frontier", "frontier-all", "lowdin", "mulliken", "summary"}
STRUCTURE_ONLY = {"structure", "molecular_metadata"}
PERIODIC_GRID = STRUCTURE_ONLY | {"periodic_cell", "volumetric_grid"}
FIXTURE_CONTRACTS = {
    "charmm": (STRUCTURE_ONLY, set(), {"structure", "metadata"}, 3),
    "chgcar": (PERIODIC_GRID, set(), {"structure", "periodic", "grids", "metadata"}, 1),
    "cp2klog": (WAVEFUNCTION | {"electronic_energy"}, MOLECULAR_ANALYSES, {"structure", "calculation", "metadata"}, 1),
    "cube": ({"volumetric_grid"}, set(), {"grids"}, None),
    "extxyz": (STRUCTURE_ONLY, set(), {"structure", "metadata"}, 3),
    "fchk": (WAVEFUNCTION | {"electronic_energy"}, MOLECULAR_ANALYSES, {"structure", "calculation", "metadata"}, 3),
    "fcidump": ({"integrals"}, set(), {"integrals"}, None),
    "gamess": (STRUCTURE_ONLY, set(), {"structure", "metadata"}, 3),
    "gaussianinput": (STRUCTURE_ONLY, set(), {"structure", "metadata"}, 3),
    "gaussianlog": ({"molecular_metadata"}, set(), {"metadata"}, None),
    "gromacs": (STRUCTURE_ONLY | {"periodic_cell"}, set(), {"structure", "periodic", "metadata"}, 3),
    "json_qcschema": (STRUCTURE_ONLY, set(), {"structure", "metadata"}, 3),
    "locpot": (PERIODIC_GRID, set(), {"structure", "periodic", "grids", "metadata"}, 1),
    "mol2": (STRUCTURE_ONLY, set(), {"structure", "metadata"}, 3),
    "molden": (WAVEFUNCTION, MOLECULAR_ANALYSES, {"structure", "calculation", "metadata"}, 3),
    "molekel": (WAVEFUNCTION, MOLECULAR_ANALYSES, {"structure", "calculation"}, 3),
    "mwfn": (WAVEFUNCTION | {"electronic_energy"}, MOLECULAR_ANALYSES, {"structure", "calculation", "metadata"}, 3),
    "orcalog": (STRUCTURE_ONLY | {"electronic_energy"}, set(), {"structure", "metadata"}, 3),
    "pdb": (STRUCTURE_ONLY | {"isolated_molecule"}, {"summary"}, {"structure", "calculation", "metadata"}, 3),
    "poscar": (STRUCTURE_ONLY | {"periodic_cell"}, set(), {"structure", "periodic", "metadata"}, 1),
    "qchemlog": (STRUCTURE_ONLY | {"electronic_energy"}, set(), {"structure", "metadata"}, 3),
    "sdf": (STRUCTURE_ONLY | {"isolated_molecule"}, {"summary"}, {"structure", "calculation", "metadata"}, 3),
    "wfn": (WAVEFUNCTION | {"electronic_energy"}, MOLECULAR_ANALYSES, {"structure", "calculation", "metadata"}, 3),
    "wfx": (WAVEFUNCTION | {"electronic_energy"}, MOLECULAR_ANALYSES, {"structure", "calculation", "metadata"}, 3),
    "xyz": (STRUCTURE_ONLY | {"isolated_molecule"}, {"summary"}, {"structure", "calculation", "metadata"}, 3),
}
NATIVE_FORMATS = {"cube", "fchk", "pdb", "sdf", "xyz"}


def put(format_id: str, filename: str, text: str) -> Path:
    target = FIXTURES / format_id / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def write_mwfn(water: iodata.IOData) -> None:
    """Write the same water orbitals in MWFN's segmented shell layout."""
    shells = []
    for shell in water.obasis.shells:
        for column, angular in enumerate(shell.angmoms):
            shells.append((shell.icenter + 1, int(angular), shell.exponents, shell.coeffs[:, column]))
    nprimitive = sum(len(exponents) for _, _, exponents, _ in shells)
    lines = [
        "openWFN water wavefunction derived from examples/water/water.fchk",
        "Wfntype= 0", "Charge= 0", "Naelec= 5", "Nbelec= 5",
        f"E_tot= {water.energy:.15f}", "VT_ratio= 2.0", "Ncenter= 3",
        "# Atom information", "$Centers",
    ]
    for index, (number, core, coords) in enumerate(
        zip(water.atnums, water.atcorenums, water.atcoords, strict=True), 1
    ):
        x, y, z = coords / angstrom
        lines.append(f"{index} X {int(number)} {float(core):.8f} {x:.12f} {y:.12f} {z:.12f}")
    lines.extend([
        "# Basis function information",
        f"Nbasis= {water.obasis.nbasis}",
        f"Nindbasis= {water.mo.norba}",
        f"Nshell= {len(shells)}",
        f"Nprimshell= {nprimitive}",
        f"Nprims= {nprimitive}",
        "$Shell types",
        " " + " ".join(str(angular) for _, angular, _, _ in shells),
        "$Shell centers",
        " " + " ".join(str(center) for center, _, _, _ in shells),
        "$Shell contraction",
        " " + " ".join(str(len(exponents)) for _, _, exponents, _ in shells),
        "$Primitive exponents",
        " ".join(f"{float(value):.14E}" for _, _, exponents, _ in shells for value in exponents),
        "$Contraction coefficients",
        " ".join(f"{float(value):.14E}" for _, _, _, coeffs in shells for value in coeffs),
        "# Orbital information",
    ])
    for index in range(water.mo.norba):
        lines.extend([
            f"Index {index + 1}", "Type 0",
            f"Energy {float(water.mo.energiesa[index]):.14E}",
            f"Occ {float(water.mo.occsa[index] + water.mo.occsb[index]):.8f}",
            "Sym A", "$Coeff",
            " ".join(f"{float(value):.14E}" for value in water.mo.coeffsa[:, index]),
        ])
    put("mwfn", "water.mwfn", "\n".join(lines) + "\n")


def write_manifest() -> None:
    """Pin independent expected components, capabilities, and analyses."""
    entries = []
    for format_id, (present, analyses, components, atom_count) in sorted(FIXTURE_CONTRACTS.items()):
        files = list((FIXTURES / format_id).iterdir())
        if len(files) != 1:
            raise ValueError(f"Expected exactly one fixture for {format_id}, got {files}")
        path = files[0]
        expected_capabilities = {
            name: ("derived" if name == "ao_overlap" else "available") if name in present else "missing"
            for name in CAPABILITIES
        }
        origin = (
            "Converted from the openWFN-owned examples/water/water.fchk calculation"
            if format_id in {"fchk", "molden", "molekel", "mol2", "mwfn", "pdb", "sdf", "wfn", "wfx", "xyz"}
            else "Constructed specifically for openWFN from the published format layout"
        )
        entries.append({
            "format_id": format_id,
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256(path.read_bytes()).hexdigest(),
            "status": "Stable",
            "provenance": {
                "origin": origin,
                "license": "MIT (openWFN project fixture)",
                "redistribution_safe": True,
                "generation": "scripts/generate_interop_fixtures.py",
            },
            "expected_source": {
                "format": format_id,
                "backend": "native" if format_id in NATIVE_FORMATS else "iodata",
                "backend_version": None if format_id in NATIVE_FORMATS else "1.0.1",
            },
            "expected_components": sorted(components),
            "expected_capabilities": expected_capabilities,
            "expected_analyses": {
                "available": sorted(analyses),
                "unsupported": sorted(set(ANALYSES) - analyses),
            },
            "expected_atom_count": atom_count,
        })
    destination = ROOT / "validation" / "interop" / "manifest.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps({"schema_version": "1.0", "formats": entries}, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    source = ROOT / "examples" / "water" / "water.fchk"
    water = iodata.load_one(str(source))

    target = FIXTURES / "fchk" / "water.fchk"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)

    for format_id, filename in (
        ("molden", "water.molden"),
        ("molekel", "water.mkl"),
        ("mol2", "water.mol2"),
        ("pdb", "water.pdb"),
        ("sdf", "water.sdf"),
        ("wfn", "water.wfn"),
        ("wfx", "water.wfx"),
        ("xyz", "water.xyz"),
    ):
        target = FIXTURES / format_id / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        iodata.dump_one(water, str(target), fmt=format_id, allow_changes=True)
    write_mwfn(water)

    put("cube", "water.cube", """openWFN synthetic one-voxel density
atomic units
    1    0.000000    0.000000    0.000000
    1    1.000000    0.000000    0.000000
    1    0.000000    1.000000    0.000000
    1    0.000000    0.000000    1.000000
    1    1.000000    0.000000    0.000000    0.000000
    0.250000
""")
    put("fcidump", "water.FCIDUMP", """ &FCI NORB=2,NELEC=2,MS2=0,
 ORBSYM=1,1,
 ISYM=1,
 &END
 0.700000000000 1 1 1 1
-1.100000000000 1 1 0 0
 0.500000000000 2 2 0 0
 0.800000000000 0 0 0 0
""")
    put("json_qcschema", "water.qcschema.json", json.dumps({
        "schema_name": "qcschema_molecule",
        "schema_version": 2,
        "symbols": ["O", "H", "H"],
        "geometry": [0.0, 0.0, 0.0, 0.0, 1.43, 1.11, 0.0, -1.43, 1.11],
        "molecular_charge": 0,
        "molecular_multiplicity": 1,
        "name": "openWFN synthetic water",
        "provenance": {"creator": "openWFN", "routine": "interoperability validation"},
    }, indent=2) + "\n")
    put("extxyz", "water.extxyz", """3
Properties=species:S:1:pos:R:3 pbc=\"F F F\" comment=\"openWFN water\"
O 0.000000 0.000000 0.000000
H 0.000000 0.756000 0.587000
H 0.000000 -0.756000 0.587000
""")
    put("gaussianinput", "water.gjf", """#p HF/STO-3G

openWFN synthetic water input

0 1
O 0.000000 0.000000 0.000000
H 0.000000 0.756000 0.587000
H 0.000000 -0.756000 0.587000

""")
    put("charmm", "water.crd", """* openWFN synthetic water coordinates
*
3
1 1 HOH O 0.000000 0.000000 0.000000 SYS 1 15.999
2 1 HOH H1 0.000000 0.756000 0.587000 SYS 1 1.008
3 1 HOH H2 0.000000 -0.756000 0.587000 SYS 1 1.008
""")
    gro_atoms = [
        ("OW", 0.0000, 0.0000, 0.0000),
        ("HW1", 0.0000, 0.0756, 0.0587),
        ("HW2", 0.0000, -0.0756, 0.0587),
    ]
    gro_lines = ["openWFN synthetic water", "3"]
    for index, (name, x, y, z) in enumerate(gro_atoms, 1):
        gro_lines.append(f"{1:5d}{'HOH':<5}{name:>5}{index:5d}{x:8.3f}{y:8.3f}{z:8.3f}")
    gro_lines.append("   2.00000   2.00000   2.00000")
    put("gromacs", "water.gro", "\n".join(gro_lines) + "\n")

    vasp_header = """openWFN synthetic periodic H
1.0
2.0 0.0 0.0
0.0 2.0 0.0
0.0 0.0 2.0
H
1
Direct
0.0 0.0 0.0
"""
    put("poscar", "POSCAR-water", vasp_header)
    grid = "\n1 1 1\n0.25\n"
    put("chgcar", "CHGCAR-water", vasp_header + grid)
    put("locpot", "LOCPOT-water", vasp_header + grid)

    put("orcalog", "water.out", """O   R   C   A
CARTESIAN COORDINATES (ANGSTROEM)
---------------------------------
O   0.000000  0.000000  0.000000
H   0.000000  0.756000  0.587000
H   0.000000 -0.756000  0.587000

CARTESIAN COORDINATES (A.U.)
-----------------------------
NO  LB  ZA  FRAG  MASS       X          Y          Z
0   O   8.0 0     15.999     0.000000   0.000000   0.000000
1   H   1.0 0      1.008     0.000000   1.428633   1.109269
2   H   1.0 0      1.008     0.000000  -1.428633   1.109269
FINAL SINGLE POINT ENERGY      -74.960000000000
""")

    put("gaussianlog", "water.log", """ Entering Gaussian System
    NBasis =     1
 *** Overlap ***
          1
    1  1.000000D+00
 Normal termination of Gaussian
""")

    put("gamess", "water.dat", """$DATA
openWFN synthetic water
C1
O 8.0 0.000000 0.000000 0.000000
H 1.0 0.000000 1.428633 1.109269
H 1.0 0.000000 -1.428633 1.109269
 $END      
 COORDINATES OF SYMMETRY UNIQUE ATOMS (ANGS)
 Header line one
 Header line two
 O 8.0 0.000000 0.000000 0.000000
 H 1.0 0.000000 0.756000 0.587000
 H 1.0 0.000000 -0.756000 0.587000
""")

    put("qchemlog", "water.qchemlog", """Q-Chem openWFN synthetic validation excerpt
$rem
jobtype sp
method hf
unrestricted false
basis sto-3g
$end
Standard Nuclear Orientation (Angstroms)
Atom     X       Y       Z
----------------------------------------
1 O 0.000000 0.000000 0.000000
2 H 0.000000 0.756000 0.587000
3 H 0.000000 -0.756000 0.587000
----------------------------------------
Nuclear repulsion energy = 8.000000 hartrees
There are 5 alpha and 5 beta electrons
Basis summary
There are 13 basis functions
Orbital Energies (a.u.)
-- Occupied --
-20.0 -1.0 -0.5 -0.4 -0.3
-- Virtual --
0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8
--------------------------------------------------------------
Total energy in the final basis set = -74.960000000000
""")

    contracted = """\n ********************** Contracted Gaussian Type Orbitals **********************
 S Functions
 1.000000 1.000000 0.000000
 0.500000 0.000000 1.000000
 *******************
"""
    cp2k = (
        " Atomic Energy Calculation                         2\n"
        + " All Electron Basis\n" + contracted
        + " Pseudopotential Basis\n" + contracted
        + " METHOD    | R\n"
        + " Electronic structure\n"
        + f"{' Energy components [Hartree]           Total Energy ::':<60}-2.000000000000\n"
        + " Orbital energies\n"
        + " state l occupation energy\n"
        + "1 0 2.0 -0.5\n"
        + "2 0 0.0  0.1\n\n\n"
        + " Atomic orbital expansion coefficients [Alpha]\n"
        + " coefficients\n"
        + "    ORBITAL      L = 0 STATE = 1\n"
        + " 2.526475110984\n 0.000000000000\n\n"
        + "    ORBITAL      L = 0 STATE = 2\n"
        + " 0.000000000000\n 1.000000000000\n\n"
    )
    put("cp2klog", "helium.cp2k.out", cp2k)
    write_manifest()


if __name__ == "__main__":
    main()
