from openwfn.interactive import (  # type: ignore
    FEATURE_ALIASES,
    print_feature_page,
    print_landing_page,
    prompt_output_filename,
)


def test_interactive_aliases_cover_feature_navigation():
    assert FEATURE_ALIASES["1"] == "summary"
    assert FEATURE_ALIASES["4"] == "dist"
    assert FEATURE_ALIASES["7"] == "xyz"
    assert FEATURE_ALIASES["8"] == "view"
    assert FEATURE_ALIASES["10"] == "graph"
    assert FEATURE_ALIASES["exit"] == "exit"


def test_prompt_output_filename_uses_default(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert prompt_output_filename("water.fchk") == "water.xyz"


def test_print_landing_page_shows_intro_and_features(capsys):
    print_landing_page("water.fchk", [8, 1, 1], {"Charge": 0, "Multiplicity": 1})
    captured = capsys.readouterr()
    output = captured.out

    assert "Open WaveFunction Network" in output
    assert "A lightweight terminal toolkit" in output
    assert "Stable Features" in output
    assert "Molecular summary" in output
    assert "Open molecule viewer" in output
    assert "Show fragments / connectivity" in output
    assert "Every page supports `back` and `exit`" in output
    assert "graph" in output


def test_print_feature_page_shows_back_and_exit(capsys):
    print_feature_page("Distance", "Measure the distance between two atoms.")
    captured = capsys.readouterr()
    output = captured.out

    assert "Distance" in output
    assert "Measure the distance between two atoms." in output
    assert "back" in output
    assert "exit" in output
