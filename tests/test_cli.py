import subprocess


def test_cli_help():
    result = subprocess.run(
        ["openwfn", "--help"],
        capture_output=True,
        text=True
    )

    # help should succeed
    assert result.returncode == 0
    assert "Usage" in result.stdout


def test_cli_basic_run(tmp_path):
    # create minimal fake fchk file for testing
    f = tmp_path / "mini.fchk"

    f.write_text("""Charge I 0
Multiplicity I 1
Number of atoms I 1
Atomic numbers I N= 1
1
Current cartesian coordinates R N= 3
0.0 0.0 0.0
""")

    # IMPORTANT: disable interactive
    result = subprocess.run(
        ["openwfn", str(f), "--no-interactive"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "Atom index table" in result.stdout
