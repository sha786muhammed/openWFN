# tests/test_constants.py

import pytest  # type: ignore
from openwfn.constants import Z_TO_SYMBOL, ATOMIC_MASS, COVALENT_RADII  # type: ignore


def test_periodic_table_completeness():
    # Check a few random elements across the table
    assert Z_TO_SYMBOL[1] == "H"
    assert Z_TO_SYMBOL[6] == "C"
    assert Z_TO_SYMBOL[17] == "Cl"
    assert Z_TO_SYMBOL[79] == "Au"
    assert Z_TO_SYMBOL[118] == "Og"

    # Check approximate size
    assert len(Z_TO_SYMBOL) >= 118


def test_atomic_masses():
    # Standard ones
    assert ATOMIC_MASS[1] == pytest.approx(1.008, 0.001)
    assert ATOMIC_MASS[6] == pytest.approx(12.011, 0.001)
    
    # Heavy ones that were missing
    assert ATOMIC_MASS[79] == pytest.approx(196.97, 0.01)  # Gold
    assert ATOMIC_MASS[92] == pytest.approx(238.03, 0.01)  # Uranium


def test_covalent_radii():
    # Check that we have radii for common organic elements
    assert "H" in COVALENT_RADII
    assert "C" in COVALENT_RADII
    
    # Check transition metals
    assert "Fe" in COVALENT_RADII
    assert "Pt" in COVALENT_RADII
    
    # Check some that might be missing in smaller lists
    assert "U" in COVALENT_RADII
