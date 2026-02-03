import math

from openwfn.geometry import angle, dihedral, distance


def test_distance():
    coordinates = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]
    assert math.isclose(distance(1, 2, coordinates), 1.0)


def test_angle():
    coordinates = [
        (1.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
    ]
    assert math.isclose(angle(1, 2, 3, coordinates), 90.0)


def test_dihedral():
    coordinates = [
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (1.0, 1.0, 0.0),
        (1.0, 1.0, 1.0),
    ]
    assert math.isclose(abs(dihedral(1, 2, 3, 4, coordinates)), 90.0)
