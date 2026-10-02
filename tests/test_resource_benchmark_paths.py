from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_relative_installed_corpus_is_resolved_before_workspace_chdir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.benchmark_resources import resolve_examples_dir

    corpus = tmp_path / "installed-examples" / "everyday-qc"
    corpus.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    resolved = resolve_examples_dir(Path("installed-examples/everyday-qc"), ROOT)

    assert resolved == corpus.resolve()
    assert resolved.is_absolute()


def test_default_corpus_is_resolved_from_repository_root(tmp_path: Path) -> None:
    from scripts.benchmark_resources import resolve_examples_dir

    root = tmp_path / "checkout"
    expected = root / "examples" / "everyday-qc"

    resolved = resolve_examples_dir(None, root)

    assert resolved == expected.resolve()
    assert resolved.is_absolute()
