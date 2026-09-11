from pathlib import Path

import pytest

from openwfn.parsers.gaussian.output import parse_gaussian_output


def test_gaussian_output_extracts_route_energy_and_status(tmp_path: Path) -> None:
    source = tmp_path / "water.log"
    source.write_text(
        " Entering Gaussian System\n"
        " #P B3LYP/6-31G(d) Opt\n"
        " ----------------------\n"
        " SCF Done:  E(RB3LYP) =  -76.4212345678 A.U. after 10 cycles\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    metadata = parse_gaussian_output(source)

    assert metadata.route == "#P B3LYP/6-31G(d) Opt"
    assert metadata.method == "B3LYP"
    assert metadata.basis == "6-31G(d)"
    assert metadata.energy_hartree == pytest.approx(-76.4212345678)
    assert metadata.terminated_normally is True
