from importlib.metadata import entry_points, version
from importlib.resources import files


def test_installed_distribution_version() -> None:
    assert version("openwfn") == "0.8.0a2"


def test_console_script_targets_cli_main() -> None:
    scripts = {item.name: item.value for item in entry_points(group="console_scripts")}
    assert scripts["openwfn"] == "openwfn.cli:main"


def test_distribution_contains_maintained_water_example() -> None:
    resource = files("openwfn.example_data").joinpath("water.fchk")

    assert resource.is_file()
    assert "Number of atoms" in resource.read_text(encoding="utf-8")
