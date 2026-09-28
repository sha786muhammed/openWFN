"""Install redistributable example inputs from the package."""

from importlib.resources import files
from pathlib import Path

EXAMPLE_FILENAMES = ("water.fchk",)


def install_examples(destination: Path, *, overwrite: bool = False) -> tuple[Path, ...]:
    """Copy maintained example inputs into *destination*."""
    destination = Path(destination)
    targets = tuple(destination / name for name in EXAMPLE_FILENAMES)
    conflicts = tuple(path for path in targets if path.exists())
    if conflicts and not overwrite:
        names = ", ".join(str(path) for path in conflicts)
        raise FileExistsError(f"example output exists: {names}; pass --overwrite to replace it")

    package = files("openwfn.example_data")
    destination.mkdir(parents=True, exist_ok=True)
    for name, target in zip(EXAMPLE_FILENAMES, targets, strict=True):
        temporary = target.with_name(f"{target.name}.tmp")
        temporary.write_bytes(package.joinpath(name).read_bytes())
        temporary.replace(target)
    return targets
