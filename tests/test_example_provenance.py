import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
PROVENANCE = EXAMPLES / "PROVENANCE.md"


def example_files() -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in EXAMPLES.rglob("*")
            if path.is_file() and path.suffix in {".fchk", ".gjf", ".xyz"}
        )
    )


def test_every_example_file_has_recorded_sha256() -> None:
    record = PROVENANCE.read_text(encoding="utf-8")

    for path in example_files():
        relative = path.relative_to(ROOT).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert relative in record
        assert digest in record


def test_validation_manifest_checksums_match_examples() -> None:
    manifest = json.loads((ROOT / "validation" / "manifest.json").read_text(encoding="utf-8"))

    active = [case for case in manifest["cases"] if case["status"] == "active"]
    assert {case["id"] for case in active} == {"water", "ammonia", "methane"}
    for case in active:
        path = ROOT / case["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == case["sha256"]


def test_packaged_water_is_byte_identical_and_documented() -> None:
    repository_copy = EXAMPLES / "water" / "water.fchk"
    packaged_copy = ROOT / "src" / "openwfn" / "example_data" / "water.fchk"
    packaged_readme = packaged_copy.with_name("README.md").read_text(encoding="utf-8")
    digest = hashlib.sha256(repository_copy.read_bytes()).hexdigest()

    assert packaged_copy.read_bytes() == repository_copy.read_bytes()
    assert digest in packaged_readme
    assert "examples/PROVENANCE.md" in packaged_readme


def test_example_provenance_preserves_unknown_gaussian_details() -> None:
    record = PROVENANCE.read_text(encoding="utf-8").lower()

    for molecule in ("water", "ammonia", "methane"):
        section = record.split(f"## {molecule}", maxsplit=1)[1].split("\n## ", maxsplit=1)[0]
        assert "gaussian version: not recorded" in section
        assert "exact gaussian invocation: not recorded" in section
        assert "rhf/3-21g" in section
        assert "charge 0" in section
        assert "multiplicity 1" in section


def test_examples_overview_lists_only_existing_file_types() -> None:
    overview = (EXAMPLES / "README.md").read_text(encoding="utf-8")
    suffixes = {path.suffix for path in example_files()}

    for suffix in suffixes:
        assert f"`{suffix}`" in overview
    assert "`.chk`" not in overview
    assert "`.log`" not in overview
