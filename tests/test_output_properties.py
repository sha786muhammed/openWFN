"""Focused regression checks for source-reported output properties."""

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from importlib.util import find_spec
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from openwfn.adapters.iodata import _omission_warnings
from openwfn.cli import main
from openwfn.output_properties import _normalize_output, read_output
from openwfn.results import ResultRecord


def fixture():
    return SimpleNamespace(
        metadata={"package": "ORCA", "package_version": "5.0.3", "success": True},
        natom=2, charge=0, mult=1,
        atomnos=np.array([1, 1]), atomcoords=np.array([[[0, 0, 0], [0, 0, 1]]]),
        scfenergies=np.array([-27.21138505]),
        homos=np.array([0]), moenergies=[np.array([-2.0, 1.0])],
        moments=[np.zeros(3), np.array([1.0, 2.0, 3.0])],
        atomcharges={"mulliken": np.array([0.2, -0.2])},
    )


class OutputPropertiesTests(unittest.TestCase):
    def test_units_indices_and_charge_conservation(self):
        data, warnings = _normalize_output(fixture())
        self.assertEqual(warnings, ())
        self.assertAlmostEqual(data["scf_energy_hartree"], -1.0)
        self.assertEqual(data["frontier_orbitals"][0]["homo_index_1based"], 1)
        self.assertEqual(data["frontier_orbitals"][0]["gap_ev"], 3.0)
        self.assertEqual(data["reported_atomic_charges"]["mulliken"]["charge_sum_residual"], 0)

    def test_unconfirmed_termination_and_missing_lumo_are_warned(self):
        parsed = fixture()
        parsed.metadata["success"] = False
        parsed.moenergies = [np.array([-2.0])]
        data, warnings = _normalize_output(parsed)
        self.assertIsNone(data["frontier_orbitals"][0]["gap_ev"])
        self.assertEqual(len(warnings), 2)

    def test_nonfinite_result_is_rejected(self):
        parsed = fixture()
        parsed.scfenergies[0] = np.nan
        data, _ = _normalize_output(parsed)
        with self.assertRaises(ValueError):
            ResultRecord(kind="output_properties", data=data)

    def test_inconsistent_atom_counts_are_rejected(self):
        parsed = fixture()
        parsed.atomcharges["mulliken"] = np.array([0.0])
        with self.assertRaises(ValueError):
            _normalize_output(parsed)

    def test_empty_charge_map_is_not_an_omission(self):
        self.assertEqual(_omission_warnings(SimpleNamespace(atcharges={})), [])

    @unittest.skipUnless(find_spec("cclib"), "optional outputs extra is not installed")
    def test_cli_and_api_share_result_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.out"
            path.write_text("mock parser input", encoding="utf-8")
            with patch("cclib.io.ccread", return_value=fixture()):
                record = read_output(path)
                stream = StringIO()
                with redirect_stdout(stream):
                    code = main(["--format", "json", str(path), "properties"])
            payload = json.loads(stream.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(payload["data"], record.data)
            self.assertEqual(payload["provenance"]["input_sha256"], record.provenance["input_sha256"])

    def test_two_orbital_channels_remain_separate(self):
        parsed = fixture()
        parsed.homos = np.array([0, 1])
        parsed.moenergies = [np.array([-2.0, 1.0]), np.array([-3.0, -1.0, 2.0])]
        data, _ = _normalize_output(parsed)
        self.assertEqual([item["channel"] for item in data["frontier_orbitals"]], ["alpha", "beta"])
        self.assertEqual(data["frontier_orbitals"][1]["homo_index_1based"], 2)

    @unittest.skipUnless(find_spec("cclib"), "optional outputs extra is not installed")
    def test_unrecognized_output_returns_json_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.out"
            path.write_text("unrecognized input", encoding="utf-8")
            stream = StringIO()
            with patch("cclib.io.ccread", return_value=None), redirect_stdout(stream):
                code = main(["--format", "json", str(path), "properties"])
            self.assertEqual(code, 4)
            self.assertEqual(json.loads(stream.getvalue())["status"], "failed")


if __name__ == "__main__":
    unittest.main()
