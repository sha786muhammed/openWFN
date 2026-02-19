import subprocess
import sys


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
        [sys.executable, "-m", "openwfn.cli", str(f), "info"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "Atoms:" in result.stdout
