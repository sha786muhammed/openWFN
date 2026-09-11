import json
from pathlib import Path

from openwfn.parsers.gaussian.fchk import parse_fchk
from openwfn.workbench.payload import WorkbenchPayload

WATER = Path(__file__).resolve().parents[2] / "examples" / "water" / "water.fchk"


def test_workbench_payload_has_versioned_scientific_contract() -> None:
    data = parse_fchk(WATER)

    payload = WorkbenchPayload.from_calculation(data)
    decoded = json.loads(payload.to_json())

    assert decoded["schema_version"] == "1.0"
    assert len(decoded["molecule"]["atoms"]) == 3
    assert decoded["molecule"]["charge"] == 0
    assert decoded["properties"]["frontier"]["homo_number"] == 5
    assert len(decoded["properties"]["mulliken"]["atomic_charges"]) == 3
    assert decoded["provenance"]["sha256"] == data.molecule.provenance.sha256
    assert decoded["fields"] == []


def test_workbench_payload_json_is_deterministic() -> None:
    data = parse_fchk(WATER)

    first = WorkbenchPayload.from_calculation(data).to_json()
    second = WorkbenchPayload.from_calculation(data).to_json()

    assert first == second
