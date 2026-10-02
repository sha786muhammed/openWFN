from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_stable_docs_do_not_blanket_validated_everyday_qc_as_experimental() -> None:
    examples = (ROOT / "examples" / "everyday-qc" / "README.md").read_text(encoding="utf-8")
    limitations = (ROOT / "docs" / "limitations.md").read_text(encoding="utf-8")

    assert "Methods remain **Experimental**" not in examples
    assert "The new MO cube/composition/Mayer/DOS/PDOS methods are Experimental" not in limitations


def test_stable_docs_distinguish_integral_and_grid_esp_status() -> None:
    limitations = (ROOT / "docs" / "limitations.md").read_text(encoding="utf-8")

    assert "Electronic and total ESP use grid quadrature and are Experimental" not in limitations
    assert "Gaussian-integral" in limitations
    assert "grid" in limitations.lower()
    assert "Experimental" in limitations
