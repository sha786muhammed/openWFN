import pytest  # type: ignore
from openwfn.fchk import parse_fchk_arrays, parse_fchk_scalars  # type: ignore


BOHR = 0.52917721092


def test_parse_fchk_scalars():
    lines = [
        "Charge                        I               0\n",
        "Multiplicity                  I               1\n",
        "Number of atoms               I               3\n",
        "Number of alpha electrons     I               5\n",
        "Number of beta electrons      I               5\n",
    ]
    scalars = parse_fchk_scalars(lines)
    assert scalars["Charge"] == 0
    assert scalars["Multiplicity"] == 1
    assert scalars["Number of atoms"] == 3
    assert scalars["Number of alpha electrons"] == 5
    assert scalars["Number of beta electrons"] == 5


def test_parse_fchk_arrays():
    lines = [
        "Atomic numbers                 I   N= 3\n",
        "1 6 8\n",
        "Current cartesian coordinates  R   N= 9\n",
        "0.0 0.0 0.0 1.0 0.0 0.0 0.0 1.0 0.0\n",
    ]
    atomic_numbers, coordinates = parse_fchk_arrays(lines)

    assert atomic_numbers == [1, 6, 8]

    assert coordinates[0] == pytest.approx((0.0, 0.0, 0.0))
    assert coordinates[1] == pytest.approx((1.0 * BOHR, 0.0, 0.0))
    assert coordinates[2] == pytest.approx((0.0, 1.0 * BOHR, 0.0))


def test_parse_fchk_arrays_rejects_malformed_coordinate_count():
    lines = [
        "Atomic numbers                 I   N= 1\n",
        "1\n",
        "Current cartesian coordinates  R   N= 4\n",
        "0.0 0.0 0.0 1.0\n",
    ]
    with pytest.raises(ValueError, match="multiple of 3"):
        parse_fchk_arrays(lines)
