import importlib
import sys


def test_iodata_format_ids_match_pinned_1_0_1_inventory() -> None:
    from openwfn.formats import iodata_format_ids

    assert iodata_format_ids() == (
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


def test_iodata_format_definitions_are_unique_sorted_and_detectable() -> None:
    from openwfn.formats import IODATA_READABLE_FORMATS

    ids = tuple(item.format_id for item in IODATA_READABLE_FORMATS)
    assert ids == tuple(sorted(ids))
    assert len(ids) == len(set(ids))
    assert all(item.patterns or item.requires_explicit_hint for item in IODATA_READABLE_FORMATS)


def test_importing_format_registry_does_not_import_iodata() -> None:
    sys.modules.pop("openwfn.formats", None)
    sys.modules.pop("iodata", None)

    importlib.import_module("openwfn.formats")

    assert "iodata" not in sys.modules
