import subprocess
import sys
import tarfile
import zipfile
from email.parser import Parser
from importlib.metadata import entry_points, version
from importlib.resources import files
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
EVERYDAY_QC_FILENAMES = {
    "ammonia.molden",
    "ammonium_cation.molden",
    "benzene.molden",
    "carbon_dioxide.molden",
    "ethanol.molden",
    "methane.molden",
    "oh_diffuse_uhf.molden",
    "oxygen_triplet.molden",
    "water.molden",
    "water_cartesian.molden",
    "water_dimer.molden",
}


@pytest.fixture(scope="module")
def built_archives(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    output = tmp_path_factory.mktemp("distribution")
    subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(output)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return next(output.glob("*.whl")), next(output.glob("*.tar.gz"))


def test_installed_distribution_version() -> None:
    assert version("openwfn") == "0.10.1"


def test_console_script_targets_cli_main() -> None:
    scripts = {item.name: item.value for item in entry_points(group="console_scripts")}
    assert scripts["openwfn"] == "openwfn.cli:main"


def test_distribution_contains_maintained_water_example() -> None:
    resource = files("openwfn.example_data").joinpath("water.fchk")

    assert resource.is_file()
    assert "Number of atoms" in resource.read_text(encoding="utf-8")


def test_distribution_contains_everyday_qc_corpus() -> None:
    suite = files("openwfn.example_data").joinpath("everyday-qc")

    assert suite.joinpath("manifest.json").is_file()
    assert suite.joinpath("README.md").is_file()
    assert {
        name for name in EVERYDAY_QC_FILENAMES if suite.joinpath(name).is_file()
    } == EVERYDAY_QC_FILENAMES


def test_built_wheel_contains_runtime_modules_assets_examples_and_notices(
    built_archives: tuple[Path, Path],
) -> None:
    wheel, _ = built_archives
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())

    expected_modules = {
        path.relative_to(ROOT / "src").as_posix()
        for path in (ROOT / "src" / "openwfn").rglob("*.py")
    }
    assert expected_modules <= names
    assert "openwfn/assets/3Dmol-min.js" in names
    assert "openwfn/example_data/README.md" in names
    assert "openwfn/example_data/water.fchk" in names
    assert "openwfn/example_data/everyday-qc/README.md" in names
    assert "openwfn/example_data/everyday-qc/manifest.json" in names
    assert {
        f"openwfn/example_data/everyday-qc/{name}" for name in EVERYDAY_QC_FILENAMES
    } <= names

    license_paths = {name for name in names if ".dist-info/licenses/" in name}
    assert any(name.endswith("/LICENSE") for name in license_paths)
    assert any(name.endswith("/THIRD_PARTY_NOTICES.md") for name in license_paths)
    assert any(name.endswith("/3Dmol-min.js.LICENSE.txt") for name in license_paths)


def test_built_wheel_declares_interop_as_optional_extra(
    built_archives: tuple[Path, Path],
) -> None:
    wheel, _ = built_archives
    with zipfile.ZipFile(wheel) as archive:
        metadata_name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        metadata = Parser().parsestr(archive.read(metadata_name).decode("utf-8"))

    assert "interop" in metadata.get_all("Provides-Extra", [])
    requirements = metadata.get_all("Requires-Dist", [])
    assert any(
        requirement.startswith("qc-iodata==1.0.1") and "interop" in requirement
        for requirement in requirements
    )
    assert not any(
        requirement.startswith("qc-iodata") and "interop" not in requirement
        for requirement in requirements
    )


def test_source_distribution_contains_project_policies_and_provenance(
    built_archives: tuple[Path, Path],
) -> None:
    _, source = built_archives
    with tarfile.open(source, "r:gz") as archive:
        names = {
            Path(name).relative_to(Path(name).parts[0]).as_posix()
            for name in archive.getnames()
        }

    assert {
        "CITATION.cff",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "CONTRIBUTORS.md",
        "LICENSE",
        "MAINTAINERS.md",
        "ROADMAP.md",
        "SECURITY.md",
        "THIRD_PARTY_NOTICES.md",
        "examples/PROVENANCE.md",
        "docs/assets/data/asset-provenance.yml",
    } <= names
