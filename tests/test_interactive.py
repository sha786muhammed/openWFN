from openwfn.interactive import (  # type: ignore
    FEATURE_ALIASES,
    print_feature_page,
    print_landing_page,
    prompt_open_in_browser,
    prompt_output_filename,
    prompt_viewer_filename,
)


def test_interactive_aliases_cover_feature_navigation():
    assert FEATURE_ALIASES["1"] == "summary"
    assert FEATURE_ALIASES["4"] == "dist"
    assert FEATURE_ALIASES["7"] == "bonds"
    assert FEATURE_ALIASES["8"] == "graph"
    assert FEATURE_ALIASES["9"] == "xyz"
    assert FEATURE_ALIASES["10"] == "view"
    assert FEATURE_ALIASES["exit"] == "exit"


def test_prompt_output_filename_uses_default(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert prompt_output_filename("water.fchk") == "water.xyz"


def test_prompt_viewer_filename_uses_default(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert prompt_viewer_filename("water.fchk") == "water_viewer.html"


def test_prompt_open_in_browser_defaults_to_no(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert prompt_open_in_browser() is False


def test_prompt_open_in_browser_accepts_yes(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")
    assert prompt_open_in_browser() is True


def test_print_landing_page_shows_intro_and_features(capsys):
    print_landing_page("water.fchk", [8, 1, 1], {"Charge": 0, "Multiplicity": 1})
    captured = capsys.readouterr()
    output = captured.out

    assert "Open WaveFunction Network" in output
    assert "openWFN" in output
    assert "Scientific geometry, topology, and structure analysis" in output
    assert "Core Analysis" in output
    assert "Structure & Connectivity" in output
    assert "Export & Viewer" in output
    assert "Molecular System Summary" in output
    assert "Launch Local 3D Molecule Viewer" in output
    assert "Fragment and Connectivity Graph" in output
    assert "Citation" in output
    assert "Muhammed Shah Shaji" in output
    assert "University of Louisville" in output
    assert "number or command name" in output.lower()
    assert "repository + exact software version" in output
    assert "  7  Detected Covalent Bond Network" in output
    assert " 10  Launch Local 3D Molecule Viewer" in output


def test_print_feature_page_shows_back_and_exit(capsys):
    print_feature_page("Distance", "Measure the distance between two atoms.")
    captured = capsys.readouterr()
    output = captured.out

    assert "Distance" in output
    assert "Measure the distance between two atoms." in output
    assert "back" in output
    assert "exit" in output
