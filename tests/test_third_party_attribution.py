import hashlib
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "src" / "openwfn" / "assets" / "3Dmol-min.js"
LICENSE = ASSET.with_name("3Dmol-min.js.LICENSE.txt")
NOTICE = ROOT / "THIRD_PARTY_NOTICES.md"


def test_vendored_3dmol_has_full_license_and_notice() -> None:
    assert LICENSE.is_file()
    assert NOTICE.is_file()

    license_text = LICENSE.read_text(encoding="utf-8")
    assert "3Dmol.js incorporates code from GLmol, Three.js, and jQuery" in license_text
    assert "Copyright (c) 2014, University of Pittsburgh and contributors" in license_text
    assert "GLmol - Molecular Viewer on WebGL/Javascript (0.47)" in license_text
    assert "Copyright (c) 2010-2012 three.js Authors" in license_text
    assert "Copyright (c) 2011 John Resig" in license_text


def test_third_party_notice_records_vendored_checksum() -> None:
    digest = hashlib.sha256(ASSET.read_bytes()).hexdigest()
    notice = NOTICE.read_text(encoding="utf-8")

    assert digest == "c24a17b28f38a6fbde99cea746e2d7414da2c60efce65fa75d5293bed204e510"
    assert digest in notice
    assert "https://github.com/3dmol/3Dmol.js" in notice
    assert "version not recoverable from the bundled file" in notice


def test_distribution_metadata_includes_third_party_license() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    license_files = metadata["tool"]["setuptools"]["license-files"]

    assert "LICENSE" in license_files
    assert "THIRD_PARTY_NOTICES.md" in license_files
    assert "src/openwfn/assets/3Dmol-min.js.LICENSE.txt" in license_files
    assert "assets/*.js" in metadata["tool"]["setuptools"]["package-data"]["openwfn"]
