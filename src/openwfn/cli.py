# src/openwfn/cli.py

import sys
import os
import subprocess
import shutil

from openwfn.fchk import read_fchk, parse_fchk_scalars, parse_fchk_arrays, print_atom_table
from openwfn.geometry import (
    distance, angle, dihedral,
    molecular_formula, center_of_mass, detect_bonds
)
from openwfn.xyz import write_xyz
from openwfn.interactive import run_interactive

def print_help():
    print("""
openWFN – Wavefunction Geometry Toolkit

Usage:
  openwfn file.fchk
  openwfn file.fchk --info
  openwfn file.fchk --dist i j
  openwfn file.fchk --angle i j k
  openwfn file.fchk --dihedral i j k l
  openwfn file.fchk --xyz out.xyz
  openwfn file.fchk --no-interactive
  openwfn file.chk --bonds
""")


def ensure_fchk(file):
    if file.endswith(".fchk"):
        return file

    if file.endswith(".chk"):
        if not shutil.which("formchk"):
            sys.exit("Error: formchk not found.")

        out = file.replace(".chk", ".fchk")
        if not os.path.exists(out):
            subprocess.run(["formchk", file, out], check=True)
        return out

    sys.exit("Error: input must be .chk or .fchk")


# -------------------------------------------------
# Main
# -------------------------------------------------

def main():

    if len(sys.argv) < 2 or "--help" in sys.argv or "-h" in sys.argv:
        print_help()
        return 0

    input_file = sys.argv[1]
    fchk_file = ensure_fchk(input_file)

    lines = read_fchk(fchk_file)
    scalars = parse_fchk_scalars(lines)
    atomic_numbers, coordinates = parse_fchk_arrays(lines)

    # ---------- info ----------
    if "--info" in sys.argv:
        formula = molecular_formula(atomic_numbers)
        com = center_of_mass(atomic_numbers, coordinates)

        print("Molecular Information")
        print("---------------------")
        print(f"Atoms: {len(atomic_numbers)}")
        print(f"Formula: {formula}")
        print(f"Charge: {scalars.get('Charge')}")
        print(f"Multiplicity: {scalars.get('Multiplicity')}")
        print(f"Center of mass: ({com[0]:.3f}, {com[1]:.3f}, {com[2]:.3f})")
        return 0

    # ---------- geometry ----------
    if "--dist" in sys.argv:
        i, j = map(int, sys.argv[-2:])
        print(distance(i, j, coordinates))
        return 0

    if "--angle" in sys.argv:
        i, j, k = map(int, sys.argv[-3:])
        print(angle(i, j, k, coordinates))
        return 0

    if "--dihedral" in sys.argv:
        i, j, k, l = map(int, sys.argv[-4:])
        print(dihedral(i, j, k, l, coordinates))
        return 0

    if "--xyz" in sys.argv:
        write_xyz(sys.argv[-1], atomic_numbers, coordinates)
        return 0
    
    if "--bonds" in sys.argv:
        bonds = detect_bonds(atomic_numbers, coordinates)
        print("Detected bonds (Å)")
        print("------------------")
        for i, j, d in bonds:
            si = atomic_numbers[i-1]
            sj = atomic_numbers[j-1]
            print(f"{i:2d}-{j:2d}  {d:6.3f}")
        return 0

    # ---------- testing mode ----------
    if "--no-interactive" in sys.argv:
        print_atom_table(atomic_numbers, coordinates)
        return 0

    # ---------- interactive ----------
    run_interactive(lines, fchk_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
