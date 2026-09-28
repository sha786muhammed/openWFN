from pathlib import Path

from openwfn.batch import run_batch

ROOT = Path(__file__).resolve().parents[2]
UHF = ROOT / "tests" / "fixtures" / "scientific" / "uhf_beta_homo.fchk"


def test_run_batch_frontier_spin_all_uses_spin_complete_analysis(tmp_path: Path) -> None:
    manifest = run_batch(
        inputs=[UHF],
        operation=None,
        analyses=("frontier",),
        workers=1,
        output_dir=tmp_path / "all",
        frontier_spin="all",
    )

    assert manifest.analyses == ("frontier-all",)
    result = manifest.records[0].results[0]
    assert result.analysis_name == "frontier-all"
    assert result.data["overall_homo_spin"] == "beta"


def test_run_batch_frontier_spin_changes_configuration_fingerprint(tmp_path: Path) -> None:
    alpha = run_batch(
        inputs=[UHF],
        operation=None,
        analyses=("frontier",),
        workers=1,
        output_dir=tmp_path / "alpha",
        frontier_spin="alpha",
    )
    complete = run_batch(
        inputs=[UHF],
        operation=None,
        analyses=("frontier",),
        workers=1,
        output_dir=tmp_path / "all",
        frontier_spin="all",
    )

    assert alpha.analyses == ("frontier",)
    assert complete.analyses == ("frontier-all",)
    assert alpha.configuration_fingerprint != complete.configuration_fingerprint


def test_run_batch_rejects_invalid_frontier_spin(tmp_path: Path) -> None:
    try:
        run_batch(
            inputs=[UHF],
            operation=None,
            analyses=("frontier",),
            workers=1,
            output_dir=tmp_path / "bad",
            frontier_spin="banana",  # type: ignore[arg-type]
        )
    except ValueError as exc:
        assert "frontier spin" in str(exc).lower()
    else:
        raise AssertionError("invalid frontier spin should raise ValueError")
