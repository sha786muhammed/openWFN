import json
import os
import subprocess
import sys
from pathlib import Path

from openwfn.cli import convert_chk_to_fchk  # type: ignore

ROOT = Path(__file__).resolve().parents[1]


def run_cli(
    args: list[str], *, env_overrides: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{ROOT / 'src'}{os.pathsep}{existing}" if existing else str(ROOT / "src")
    env.update(env_overrides or {})
    return subprocess.run(
        [sys.executable, "-m", "openwfn.cli", *args],
        capture_output=True,
        text=True,
        env=env,
    )


def test_cli_help():
    result = run_cli(["--help"])

    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()
    assert "density             ==SUPPRESS==" not in result.stdout
    assert "mo                  ==SUPPRESS==" not in result.stdout


def test_cli_basic_run(tmp_path):
    # create minimal fake fchk file
    f = tmp_path / "mini.fchk"

    f.write_text("""Charge I 0
Multiplicity I 1
Number of atoms I 1
Atomic numbers I N= 1
1
Current cartesian coordinates R N= 3
0.0 0.0 0.0
""")

    result = run_cli([str(f), "summary"])

    assert result.returncode == 0
    assert "Atoms:" in result.stdout


def test_cli_hirshfeld_population_json_contract():
    result = run_cli([
        "--format",
        "json",
        "examples/water/water.fchk",
        "population",
        "hirshfeld",
    ])

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["kind"] == "hirshfeld_population"
    assert payload["status"] == "success"
    assert payload["validation_status"] == "Validated"
    assert payload["data"]["method"] == "Hirshfeld"
    assert payload["data"]["reference_library"]["id"] == "openwfn-hirshfeld-proatoms-v1"
    assert payload["data"]["diagnostics"]["charge_closure_residual"] <= 5.0e-3


def test_cli_hirshfeld_expert_grid_controls_are_explicit():
    result = run_cli([
        "--format",
        "json",
        "examples/water/water.fchk",
        "population",
        "hirshfeld",
        "--radial-points",
        "8",
        "--theta-points",
        "4",
        "--phi-points",
        "8",
        "--radial-extent",
        "0.5",
        "--chunk-size",
        "512",
    ])

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "partial"
    assert payload["data"]["quadrature"]["radial_points"] == 8
    assert payload["data"]["quadrature"]["theta_points"] == 4
    assert payload["data"]["quadrature"]["phi_points"] == 8
    assert payload["data"]["quadrature"]["radial_extent_bohr"] == 0.5
    assert payload["data"]["quadrature"]["chunk_size"] == 512
    assert payload["data"]["diagnostics"]["charge_closure_residual"] > 0.1


def test_cli_invalid_geometry_returns_nonzero():
    result = run_cli(["examples/water/water.fchk", "dist", "0", "1"])

    assert result.returncode == 1
    assert "Atom index out of range" in result.stderr


def test_cli_view_export_no_open(tmp_path):
    f = tmp_path / "mini.fchk"
    out = tmp_path / "viewer.html"

    f.write_text("""Charge I 0
Multiplicity I 1
Number of atoms I 1
Atomic numbers I N= 1
1
Current cartesian coordinates R N= 3
0.0 0.0 0.0
""")

    result = run_cli([str(f), "view", "--save", str(out)])

    assert result.returncode == 0
    assert out.exists()
    assert "standalone molecule viewer exported to" in result.stdout.lower()


def test_cli_view_defaults_to_local_html_export(tmp_path):
    f = tmp_path / "mini.fchk"
    default_out = Path.cwd() / "mini_viewer.html"

    f.write_text("""Charge I 0
Multiplicity I 1
Number of atoms I 1
Atomic numbers I N= 1
1
Current cartesian coordinates R N= 3
0.0 0.0 0.0
""")

    if default_out.exists():
        default_out.unlink()

    result = run_cli([str(f), "view"])

    try:
        assert result.returncode == 0
        assert default_out.exists()
        assert "standalone molecule viewer exported to" in result.stdout.lower()
        assert "no extra viewer assets are required" in result.stdout.lower()
    finally:
        if default_out.exists():
            default_out.unlink()


def test_chk_conversion_error_is_actionable(tmp_path):
    chk = tmp_path / "mini.chk"
    chk.write_text("placeholder")

    result = run_cli([str(chk), "summary"], env_overrides={"PATH": str(tmp_path)})

    assert result.returncode != 0
    assert "requires `formchk`" in result.stderr
    assert "formchk input.chk output.fchk" in result.stderr


def test_formchk_command_requires_chk_input(tmp_path):
    fchk = tmp_path / "mini.fchk"
    fchk.write_text("placeholder")

    result = run_cli([str(fchk), "formchk"])

    assert result.returncode == 1
    assert "requires a Gaussian `.chk` input file" in result.stderr


def test_convert_chk_to_fchk_uses_requested_output(monkeypatch, tmp_path):
    chk = tmp_path / "mini.chk"
    chk.write_text("placeholder")
    out = tmp_path / "converted.fchk"
    calls: list[list[str]] = []

    monkeypatch.setattr("openwfn.cli.shutil.which", lambda name: "/usr/bin/formchk" if name == "formchk" else None)
    monkeypatch.setattr("openwfn.cli.os.path.exists", lambda path: False)

    def fake_run(cmd: list[str], check: bool) -> None:
        assert check is True
        calls.append(cmd)

    monkeypatch.setattr("openwfn.cli.subprocess.run", fake_run)

    result = convert_chk_to_fchk(str(chk), str(out), quiet=True)

    assert result == str(out)
    assert calls == [["formchk", str(chk), str(out)]]


def test_convert_chk_to_fchk_reports_reuse(monkeypatch, tmp_path, capsys):
    chk = tmp_path / "mini.chk"
    chk.write_text("placeholder")
    out = tmp_path / "mini.fchk"

    monkeypatch.setattr("openwfn.cli.shutil.which", lambda name: "/usr/bin/formchk" if name == "formchk" else None)
    monkeypatch.setattr("openwfn.cli.os.path.exists", lambda path: str(path) == str(out))

    result = convert_chk_to_fchk(str(chk))
    captured = capsys.readouterr()

    assert result == str(out)
    assert "Reusing existing formatted checkpoint" in captured.out
