from openwfn.geometry import detect_bonds  # type: ignore

def test_water_bonds():
    atomic_numbers = [8, 1, 1]
    coordinates = [
        (0.000, 0.000, 0.000),
        (0.758, 0.000, 0.504),
        (-0.758, 0.000, 0.504),
    ]

    bonds = detect_bonds(atomic_numbers, coordinates)
    assert len(bonds) == 2
