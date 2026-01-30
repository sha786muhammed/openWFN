import sys
from openwfn.fchk import (
    read_fchk,
    parse_fchk_scalars,
    parse_fchk_arrays,
    print_atom_table,
    distance,
    angle,
    dihedral,
)


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  openwfn <file.fchk>")
        print("  openwfn <file.fchk> --dist i j")
        sys.exit(1)

    fchk_file = sys.argv[1]

    lines = read_fchk(fchk_file)
    scalars = parse_fchk_scalars(lines)
    atomic_numbers, coordinates = parse_fchk_arrays(lines)

    # Distance mode
    if len(sys.argv) == 5 and sys.argv[2] == "--dist":
        i = int(sys.argv[3])
        j = int(sys.argv[4])

        d = distance(i, j, coordinates)

        print(f"Distance between atom {i} and atom {j}: {d:.6f} Å")
        return
    
        # Angle mode
    if len(sys.argv) == 6 and sys.argv[2] == "--angle":
        i = int(sys.argv[3])
        j = int(sys.argv[4])
        k = int(sys.argv[5])

        ang = angle(i, j, k, coordinates)
        print(f"Angle ({i}-{j}-{k}): {ang:.3f} degrees")
        return
    
        # Dihedral mode
    if len(sys.argv) == 7 and sys.argv[2] == "--dihedral":
        i = int(sys.argv[3])
        j = int(sys.argv[4])
        k = int(sys.argv[5])
        l = int(sys.argv[6])

        dih = dihedral(i, j, k, l, coordinates)
        print(f"Dihedral ({i}-{j}-{k}-{l}): {dih:.3f} degrees")
        return



    # Default: print atom table
    print(f"File: {fchk_file}")
    print(f"Charge: {scalars.get('Charge')}")
    print(f"Multiplicity: {scalars.get('Multiplicity')}")
    print()

    print_atom_table(atomic_numbers, coordinates)


if __name__ == "__main__":
    main()
