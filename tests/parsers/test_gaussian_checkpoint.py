from pathlib import Path

import pytest

from openwfn.errors import ExternalProgramError
from openwfn.parsers.gaussian.checkpoint import resolve_checkpoint


def test_checkpoint_reports_missing_formchk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint = tmp_path / "water.chk"
    checkpoint.write_bytes(b"binary")
    monkeypatch.setenv("PATH", str(tmp_path))

    with pytest.raises(ExternalProgramError, match="formchk input.chk output.fchk"):
        resolve_checkpoint(checkpoint)


def test_checkpoint_runner_creates_requested_fchk(tmp_path: Path) -> None:
    checkpoint = tmp_path / "water.chk"
    checkpoint.write_bytes(b"binary")
    output = tmp_path / "converted.fchk"

    def runner(command: list[str]) -> None:
        assert command[1:] == [str(checkpoint), str(output)]
        output.write_text("formatted", encoding="utf-8")

    result = resolve_checkpoint(
        checkpoint,
        output=output,
        runner=runner,
        executable="/gaussian/formchk",
    )

    assert result == output
