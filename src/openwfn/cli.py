# src/openwfn/cli.py

import sys
import os
import subprocess
import shutil

from openwfn.fchk import (
    read_fchk,
    parse_fchk_scalars,
    parse_fchk_arrays,
    print_atom_table,
)
from openwfn.geometry import distance, angle, dihedral
from openwfn.xyz import write_xyz
from openwfn.interactive import run_interactive


def ensure_fchk(input_file):
    """Handle .chk → .fchk conversion if needed."""
    if input_file.endswith(".fchk"):
        return input_file

    if input_file.endswith(".chk"):
        if not shutil.which("formchk"):
            sys.exit("Error: 'formchk' not found in PATH.")

        fchk = input_file.replace(".chk", ".fchk")

        if not os.path.exists(fchk):
            print(f"Converting {input_file} → {fchk}")
            subprocess.run(["formchk", input_file, fchk], check=True)

        return fchk

    sys.exit("Error: input file must be .chk or .fchk")


def main():
    
    if len(sys.argv) < 2 or "--help" in sys.argv or "-h" in sys.argv:
        print("Usage:")
        print("  openwfn <file.chk|file.fchk>")
        print("  openwfn <file.fchk> --dist i j")
        print("  openwfn <file.fchk> --angle i j k")
        print("  openwfn <file.fchk> --dihedral i j k l")
        print("  openwfn <file.fchk> --xyz out.xyz")
        print("  openwfn <file.fchk> --no-interactive")
        return


    input_file = sys.argv[1]
    fchk_file = ensure_fchk(input_file)

    lines = read_fchk(fchk_file)
    scalars = parse_fchk_scalars(lines)
    atomic_numbers, coordinates = parse_fchk_arrays(lines)

    # ---------- CLI modes ----------
    if "--dist" in sys.argv:
        i, j = map(int, sys.argv[-2:])
        d = distance(i, j, coordinates)
        print(f"Distance between atom {i} and atom {j}: {d:.6f} Å")
        return

    if "--angle" in sys.argv:
        i, j, k = map(int, sys.argv[-3:])
        a = angle(i, j, k, coordinates)
        print(f"Angle ({i}-{j}-{k}): {a:.3f}°")
        return

    if "--dihedral" in sys.argv:
        i, j, k, l = map(int, sys.argv[-4:])
        d = dihedral(i, j, k, l, coordinates)
        print(f"Dihedral ({i}-{j}-{k}-{l}): {d:.3f}°")
        return

    if "--xyz" in sys.argv:
        out = sys.argv[-1]
        write_xyz(out, atomic_numbers, coordinates)
        print(f"XYZ file written to {out}")
        return
    # ---------- NON-INTERACTIVE (for testing) ----------
    if "--no-interactive" in sys.argv:
        print_atom_table(atomic_numbers, coordinates)
        return

    # ---------- DEFAULT: INTERACTIVE MODE ----------
    run_interactive(lines, fchk_file)


if __name__ == "__main__":
    main()
