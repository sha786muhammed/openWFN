from openwfn.palette import WORKFLOWS, filter_workflows, run_palette


def test_palette_search_filters_workflows_case_insensitively() -> None:
    matches = filter_workflows(WORKFLOWS, "DENSITY")

    assert [item.command for item in matches] == ["density"]


def test_palette_quit_returns_success_without_running_operation() -> None:
    choices = iter(["q"])

    code = run_palette(
        header="openWFN 0.7.0 / water.fchk",
        prompt=lambda _items: next(choices),
        dispatch=lambda _command: 99,
    )

    assert code == 0


def test_palette_dispatches_typed_command_name() -> None:
    commands: list[str] = []

    code = run_palette(
        header="openWFN 0.7.0 / water.fchk",
        prompt=lambda _items: "geometry",
        dispatch=lambda command: commands.append(command) or 0,
    )

    assert code == 0
    assert commands == ["geometry"]
