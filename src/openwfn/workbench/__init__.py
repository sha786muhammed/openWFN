"""Offline scientific workbench export."""

from pathlib import Path

from ..model import CalculationData
from ..results import ResultRecord
from . import export as _export
from .payload import WorkbenchPayload

export_workbench = _export.export_workbench


def export_workbench_record(
    data: CalculationData,
    path: Path,
    *,
    overwrite: bool = False,
) -> ResultRecord:
    """Export the offline workbench and return the established result envelope."""

    exported = export_workbench(data, path, overwrite=overwrite)
    return ResultRecord(
        kind="molecular_workbench",
        data={
            "output": str(exported),
            "offline": True,
            "schema_version": "1.0",
        },
        validation_status="Stable",
    )


# Preserve the historical direct import path used by CLI/guided-mode consumers:
# ``from openwfn.workbench.export import export_workbench_record``.
_export.export_workbench_record = export_workbench_record

__all__ = ["WorkbenchPayload", "export_workbench", "export_workbench_record"]
