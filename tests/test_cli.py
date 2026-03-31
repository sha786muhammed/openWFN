import subprocess
import sys

from openwfn import __version__  # type: ignore


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "-m", "openwfn.cli", "--help"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


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

    result = subprocess.run(
        [sys.executable, "-m", "openwfn.cli", str(f), "summary"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "Atoms:" in result.stdout


def test_cli_invalid_geometry_returns_nonzero():
    result = subprocess.run(
        [sys.executable, "-m", "openwfn.cli", "examples/water/water.fchk", "dist", "0", "1"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 1
    assert "Atom index out of range" in result.stderr


def test_runtime_version_matches_project_version():
    assert __version__ == "0.5.0"


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

    result = subprocess.run(
        [sys.executable, "-m", "openwfn.cli", str(f), "view", "--save", str(out), "--no-open"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert out.exists()
    assert "successfully exported" in result.stdout.lower()
