"""Install redistributable example inputs from the package."""

from importlib.resources import files
from pathlib import Path

EXAMPLE_FILENAMES = ("water.fchk",)
EVERYDAY_QC_FILENAMES = (
    "ammonia.molden",
    "ammonium_cation.molden",
    "benzene.molden",
    "carbon_dioxide.molden",
    "ethanol.molden",
    "methane.molden",
    "oh_diffuse_uhf.molden",
    "oxygen_triplet.molden",
    "water.molden",
    "water_cartesian.molden",
    "water_dimer.molden",
)
EVERYDAY_QC_AUXILIARY_FILENAMES = ("README.md", "manifest.json")


def _copy_resource(resource, target: Path) -> None:
    temporary = target.with_name(f"{target.name}.tmp")
    temporary.write_bytes(resource.read_bytes())
    temporary.replace(target)


def install_examples(destination: Path, *, overwrite: bool = False) -> tuple[Path, ...]:
    """Copy maintained example inputs into *destination*.

    The historical return value remains the top-level maintained examples. The
    complete versioned everyday-QC corpus is installed into ``everyday-qc/`` so
    wheel users can reproduce the same bounded workflows used by release CI.
    """
    destination = Path(destination)
    targets = tuple(destination / name for name in EXAMPLE_FILENAMES)
    everyday_qc_destination = destination / "everyday-qc"
    everyday_qc_names = EVERYDAY_QC_FILENAMES + EVERYDAY_QC_AUXILIARY_FILENAMES
    everyday_qc_targets = tuple(everyday_qc_destination / name for name in everyday_qc_names)
    conflicts = tuple(path for path in (*targets, *everyday_qc_targets) if path.exists())
    if conflicts and not overwrite:
        names = ", ".join(str(path) for path in conflicts)
        raise FileExistsError(f"example output exists: {names}; pass --overwrite to replace it")

    package = files("openwfn.example_data")
    destination.mkdir(parents=True, exist_ok=True)
    everyday_qc_destination.mkdir(parents=True, exist_ok=True)
    for name, target in zip(EXAMPLE_FILENAMES, targets, strict=True):
        _copy_resource(package.joinpath(name), target)
    everyday_qc_package = package.joinpath("everyday-qc")
    for name, target in zip(everyday_qc_names, everyday_qc_targets, strict=True):
        _copy_resource(everyday_qc_package.joinpath(name), target)
    return targets
