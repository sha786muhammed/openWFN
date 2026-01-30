
import sys
from openwfn.fchk import (
    read_fchk,
    parse_fchk_scalars,
    parse_fchk_arrays,
    print_atom_table,
)


def main():
    if len(sys.argv) != 2:
        print("Usage: openwfn <file.fchk>")
        sys.exit(1)

    fchk_file = sys.argv[1]

    lines = read_fchk(fchk_file)
    scalars = parse_fchk_scalars(lines)
    atomic_numbers, coordinates = parse_fchk_arrays(lines)

    print(f"File: {fchk_file}")
    print(f"Charge: {scalars.get('Charge')}")
    print(f"Multiplicity: {scalars.get('Multiplicity')}")
    print()

    print_atom_table(atomic_numbers, coordinates)


if __name__ == "__main__":
    main()
