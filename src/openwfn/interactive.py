# src/openwfn/interactive.py

from openwfn.fchk import (
    parse_fchk_scalars,
    parse_fchk_arrays,
    print_atom_table,
)
from openwfn.geometry import distance, angle, dihedral
from openwfn.xyz import write_xyz


def safe_int(prompt):
    """Safely read an integer from user input."""
    try:
        return int(input(prompt))
    except ValueError:
        print("Invalid input. Please enter an integer.\n")
        return None


def run_interactive(lines, filename):
    scalars = parse_fchk_scalars(lines)
    atomic_numbers, coordinates = parse_fchk_arrays(lines)
    natoms = len(atomic_numbers)

    print("\nopenWFN Interactive Mode")
    print("------------------------")
    print(f"File: {filename}\n")

    while True:
        print("Select an option:")
        print("1. Molecular information")
        print("2. Atom index table")
        print("3. Distance between two atoms")
        print("4. Bond angle (i–j–k)")
        print("5. Dihedral angle (i–j–k–l)")
        print("6. Export XYZ")
        print("7. Detect bonds")
        print("0. Exit")

        choice = input("\nEnter choice: ").strip()

        # ---------- Molecular info ----------
        if choice == "1":
            print("\nMolecular information")
            print("---------------------")
            for k, v in scalars.items():
                print(f"{k}: {v}")
            print()

        # ---------- Atom table ----------
        elif choice == "2":
            print()
            print_atom_table(atomic_numbers, coordinates)
            print()

        # ---------- Distance ----------
        elif choice == "3":
            i = safe_int("Enter atom i: ")
            j = safe_int("Enter atom j: ")
            if i is None or j is None:
                continue
            if not (1 <= i <= natoms and 1 <= j <= natoms):
                print("Atom index out of range.\n")
                continue

            d = distance(i, j, coordinates)
            print(f"\nDistance between atom {i} and atom {j}: {d:.6f} Å\n")

        # ---------- Angle ----------
        elif choice == "4":
            i = safe_int("Enter atom i: ")
            j = safe_int("Enter atom j: ")
            k = safe_int("Enter atom k: ")
            if None in (i, j, k):
                continue
            if not all(1 <= x <= natoms for x in (i, j, k)):
                print("Atom index out of range.\n")
                continue

            ang = angle(i, j, k, coordinates)
            print(f"\nBond angle ({i}-{j}-{k}): {ang:.3f}°\n")

        # ---------- Dihedral ----------
        elif choice == "5":
            i = safe_int("Enter atom i: ")
            j = safe_int("Enter atom j: ")
            k = safe_int("Enter atom k: ")
            l = safe_int("Enter atom l: ")
            if None in (i, j, k, l):
                continue
            if not all(1 <= x <= natoms for x in (i, j, k, l)):
                print("Atom index out of range.\n")
                continue

            dih = dihedral(i, j, k, l, coordinates)
            print(f"\nDihedral angle ({i}-{j}-{k}-{l}): {dih:.3f}°\n")

        # ---------- Bond detection ----------
        elif choice == "7":
            from openwfn.geometry import detect_bonds
            bonds = detect_bonds(atomic_numbers, coordinates)

            print("\nDetected bonds (Å)")
            print("------------------")

            if not bonds:
                print("No bonds detected.\n")
            else:
                for i, j, d in bonds:
                    print(f"{i:2d}-{j:2d}  {d:6.3f}")
                print()

        # ---------- XYZ export ----------
        elif choice == "6":
            out = input("Enter output XYZ filename: ").strip()
            if not out:
                print("Filename cannot be empty.\n")
                continue

            write_xyz(out, atomic_numbers, coordinates)
            print(f"\nXYZ file written to {out}\n")

        # ---------- Exit ----------
        elif choice == "0":
            print("\nExiting openWFN.")
            break

        else:
            print("Invalid option. Please try again.\n")
