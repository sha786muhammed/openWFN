import subprocess
import sys

from openwfn.formats import IODATA_READABLE_FORMATS, iodata_format_ids

EXPECTED_FORMAT_IDS = (
    "charmm",
    "chgcar",
    "cp2klog",
    "cube",
    "extxyz",
    "fcidump",
    "fchk",
    "gamess",
    "gaussianinput",
    "gaussianlog",
    "gromacs",
    "json_qcschema",
    "locpot",
    "mol2",
    "molden",
    "molekel",
    "mwfn",
    "orcalog",
    "pdb",
    "poscar",
    "qchemlog",
    "sdf",
    "wfn",
    "wfx",
    "xyz",
)


def test_iodata_format_ids_match_pinned_101_inventory() -> None:
    assert iodata_format_ids() == EXPECTED_FORMAT_IDS


def test_iodata_format_definitions_are_unique_sorted_and_detectable() -> None:
    ids = tuple(item.format_id for item in IODATA_READABLE_FORMATS)

    assert ids == tuple(sorted(ids))
    assert len(ids) == len(set(ids))
    assert all(item.patterns or item.requires_explicit_hint for item in IODATA_READABLE_FORMATS)


def test_importing_format_registry_does_not_import_iodata() -> None:
    script = """
import sys
import openwfn.formats
assert 'iodata' not in sys.modules
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
