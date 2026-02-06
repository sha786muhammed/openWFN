# src/openwfn/constants.py

# Periodic table (extend anytime)
Z_TO_SYMBOL = {
    1: "H",   2: "He",
    3: "Li",  4: "Be",
    5: "B",   6: "C",
    7: "N",   8: "O",
    9: "F",  10: "Ne",
    11: "Na", 12: "Mg",
    13: "Al", 14: "Si",
    15: "P",  16: "S",
    17: "Cl", 18: "Ar",
    19: "K",  20: "Ca",
}

ATOMIC_MASS = {
    1: 1.008,
    6: 12.011,
    7: 14.007,
    8: 15.999,
    9: 18.998,
    15: 30.974,
    16: 32.06,
    17: 35.45,
}

# Covalent radii in Å
COVALENT_RADII = {
    "H": 0.31,
    "C": 0.76,
    "N": 0.71,
    "O": 0.66,
    "F": 0.57,
    "P": 1.07,
    "S": 1.05,
    "Cl": 1.02,
}

BOHR_TO_ANGSTROM = 0.52917721092
