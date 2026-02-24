from . import commands as cmd  # type: ignore
from . import utils  # type: ignore
from .fchk import parse_fchk_scalars, parse_fchk_arrays # type: ignore


def safe_int(prompt):
    """Safely read an integer from user input."""
    try:
        val = input(prompt).strip()
        if not val:
            return None
        return int(val)
    except ValueError:
        utils.print_error("Invalid input. Please enter an integer.\n")
        return None


def run_interactive(lines, filename):
    scalars = parse_fchk_scalars(lines)
    atomic_numbers, coordinates = parse_fchk_arrays(lines)
    natoms = len(atomic_numbers)

    utils.print_header(f"openWFN Interactive Mode — {filename}")

    while True:
        print("\033[1mMain Menu:\033[0m")
        print("s. Molecular summary (Quick view)")
        print("1. Detailed metadata")
        print("2. Atom index table")
        print("3. Distance between two atoms")
        print("4. Bond angle (i–j–k)")
        print("5. Dihedral angle (i–j–k–l)")
        print("6. Export XYZ")
        print("7. Detect bonds / fragments")
        print("0. Exit")

        choice = input(f"\n{utils.highlight('openwfn')} > ").strip().lower()

        # ---------- Summary ----------
        if choice == "s":
            cmd.cmd_summary(scalars, atomic_numbers, coordinates)

        # ---------- Detailed info ----------
        elif choice == "1":
            cmd.cmd_info(scalars, atomic_numbers, coordinates)

        # ---------- Atom table ----------
        elif choice == "2":
            from .fchk import print_atom_table  # type: ignore
            utils.print_header("Coordinate Table")
            print_atom_table(atomic_numbers, coordinates)
            print()

        # ---------- Distance ----------
        elif choice == "3":
            i = safe_int("Enter first atom index: ")
            j = safe_int("Enter second atom index: ")
            if i is not None and j is not None:
                cmd.cmd_dist(i, j, coordinates)

        # ---------- Angle ----------
        elif choice == "4":
            i = safe_int("Enter atom i: ")
            j = safe_int("Enter atom j: ")
            k = safe_int("Enter atom k: ")
            if all(v is not None for v in (i, j, k)):
                cmd.cmd_angle(i, j, k, coordinates) # type: ignore

        # ---------- Dihedral ----------
        elif choice == "5":
            i = safe_int("Enter atom i: ")
            j = safe_int("Enter atom j: ")
            k = safe_int("Enter atom k: ")
            l = safe_int("Enter atom l: ")
            if all(v is not None for v in (i, j, k, l)):
                cmd.cmd_dihedral(i, j, k, l, coordinates) # type: ignore

        # ---------- Bond detection ----------
        elif choice == "7":
            cmd.cmd_graph(atomic_numbers, coordinates)

        # ---------- XYZ export ----------
        elif choice == "6":
            out = input("Enter output XYZ filename: ").strip()
            if out:
                cmd.cmd_xyz(out, atomic_numbers, coordinates)
            else:
                utils.print_error("Filename cannot be empty.")

        # ---------- Exit ----------
        elif choice == "0" or choice == "q":
            print("\nExiting openWFN.")
            break

        else:
            utils.print_error("Invalid option. Please try again.")
