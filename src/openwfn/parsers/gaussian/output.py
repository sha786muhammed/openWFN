"""Conservative metadata parser for Gaussian log and output files."""

import re
from pathlib import Path

from ...model import CalculationMetadata

_SCF_ENERGY = re.compile(r"SCF Done:\s+E\([^)]+\)\s*=\s*([-+0-9.DEde]+)")


def parse_gaussian_output(path: Path) -> CalculationMetadata:
    """Extract route, method, basis, energy, and termination state."""

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    route_lines = [line.strip() for line in lines if line.lstrip().startswith("#")]
    route = " ".join(route_lines) if route_lines else None
    method: str | None = None
    basis: str | None = None
    if route:
        method_basis = next((token for token in route.split() if "/" in token), None)
        if method_basis:
            method, basis = method_basis.split("/", maxsplit=1)

    energy: float | None = None
    for line in lines:
        match = _SCF_ENERGY.search(line)
        if match:
            energy = float(match.group(1).replace("D", "E").replace("d", "e"))

    return CalculationMetadata(
        source_program="Gaussian",
        route=route,
        method=method,
        basis=basis,
        energy_hartree=energy,
        terminated_normally=any("Normal termination of Gaussian" in line for line in lines),
    )
