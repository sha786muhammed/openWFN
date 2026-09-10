from importlib.metadata import entry_points, version


def test_installed_distribution_version() -> None:
    assert version("openwfn") == "0.6.1"


def test_console_script_targets_cli_main() -> None:
    scripts = {item.name: item.value for item in entry_points(group="console_scripts")}
    assert scripts["openwfn"] == "openwfn.cli:main"
