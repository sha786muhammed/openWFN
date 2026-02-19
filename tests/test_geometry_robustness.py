# tests/test_geometry_robustness.py

import pytest
from openwfn.geometry import center_of_mass, detect_bonds
from openwfn.constants import ATOMIC_MASS

def test_center_of_mass_unknown_element():
    # Z=999 doesn't exist
    atomic_numbers = [999]
    coordinates = [(0.0, 0.0, 0.0)]
    
    with pytest.raises(ValueError, match="Unknown atomic mass"):
        center_of_mass(atomic_numbers, coordinates)

def test_center_of_mass_valid():
    # H2 molecule
    atomic_numbers = [1, 1]
    coordinates = [(-0.37, 0.0, 0.0), (0.37, 0.0, 0.0)]
    
    cm = center_of_mass(atomic_numbers, coordinates)
    assert cm == pytest.approx((0.0, 0.0, 0.0))


def test_detect_bonds_missing_radius():
    # Z=118 (Oganesson) might have a radius if we used the full table, 
    # but let's assume we want to test when it's logically missing or we force a missing one.
    # Since we populated EVERYTHING in constants.py, getting a 'None' is hard unless we use a fake Z.
    
    # Let's temporarily mock the constants or just use a fake unknown Z (e.g. 150)
    # Z=150 is not in our periodic table (yet).
    
    atomic_numbers = [1, 150]
    # H at origin, Element 150 at 1.0 A
    coordinates = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]
    
    # Should not crash, just find no bonds because 150 has no radius
    bonds = detect_bonds(atomic_numbers, coordinates)
    assert len(bonds) == 0
