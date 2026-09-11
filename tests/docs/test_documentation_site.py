import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_check(root: Path, markdown: str) -> subprocess.CompletedProcess[str]:
    docs = root / "docs"
    docs.mkdir()
    (docs / "index.md").write_text(markdown, encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "openwfn"\nversion = "0.7.0"\n', encoding="utf-8"
    )
    (root / "mkdocs.yml").write_text(
        "site_name: openWFN\nnav:\n  - Home: index.md\n", encoding="utf-8"
    )
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_docs.py"), "--root", str(root)],
        text=True,
        capture_output=True,
        check=False,
    )


def test_check_docs_rejects_unresolved_internal_links(tmp_path: Path) -> None:
    result = run_check(tmp_path, markdown="[Missing](missing.md)")

    assert result.returncode == 1
    assert "missing.md" in result.stderr


def test_check_docs_rejects_raw_display_latex(tmp_path: Path) -> None:
    result = run_check(tmp_path, markdown=r"\[ E = mc^2 \]")

    assert result.returncode == 1
    assert "unsupported equation delimiter" in result.stderr


def test_check_docs_rejects_private_paths(tmp_path: Path) -> None:
    result = run_check(tmp_path, markdown="/Users/example/private/file.fchk")

    assert result.returncode == 1
    assert "private or machine-specific content" in result.stderr


def test_mkdocs_navigation_references_existing_pages() -> None:
    config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    referenced = re.findall(r":\s+([\w/-]+\.md)\s*$", config, flags=re.MULTILINE)

    assert referenced
    for relative in referenced:
        assert (ROOT / "docs" / relative).is_file(), relative


def test_mkdocs_loads_scholarly_theme_and_mathjax() -> None:
    config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")

    assert "stylesheets/extra.css" in config
    assert "javascripts/mathjax.js" in config
    assert "cdn.jsdelivr.net/npm/mathjax@3" in config
    assert "navigation.tabs" in config
    assert "navigation.footer" in config


def test_public_images_have_provenance_and_are_bounded() -> None:
    manifest_path = ROOT / "docs" / "assets" / "data" / "asset-provenance.yml"
    image_root = ROOT / "docs" / "assets" / "images"

    assert manifest_path.is_file()
    manifest = manifest_path.read_text(encoding="utf-8")
    images = tuple(image_root.glob("*"))
    assert images
    for image in images:
        assert image.stat().st_size < 500_000
        assert f"  {image.name}:" in manifest
        assert "    alt:" in manifest
        assert "    license:" in manifest


def test_homepage_contains_identity_paths_and_trust_links() -> None:
    home = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")

    for phrase in (
        "From checkpoint data to defensible molecular insight.",
        "For researchers",
        "For students",
        "For developers",
        "Validation",
        "Limitations",
        "Citation",
    ):
        assert phrase in home


def test_homepage_uses_compact_product_components() -> None:
    home = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    styles = (ROOT / "docs" / "stylesheets" / "extra.css").read_text(encoding="utf-8")

    for component in (
        "ow-hero", "ow-hero__copy", "ow-hero__visual", "ow-feature-grid",
        "ow-terminal", "ow-proof-strip",
    ):
        assert component in home
        assert f".{component}" in styles
    assert "grid-template-columns: minmax(0, 1.12fr) minmax(17rem, 0.88fr)" in styles
    assert "max-height: 34rem" in styles
    assert "4.7rem" not in styles


def test_material_icon_library_and_brand_identity_are_configured() -> None:
    config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")

    assert "logo: assets/images/openwfn-wordmark.png" in config
    assert "pymdownx.emoji" in config
    assert "material.extensions.emoji.twemoji" in config
    assert "material.extensions.emoji.to_svg" in config


def test_readme_opens_with_visual_product_identity() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert '<p align="center">' in readme
    assert "openwfn-orbital-hero.webp" in readme
    assert "Wavefunction analysis for reproducible molecular insight" in readme


def test_molecular_signal_wordmark_is_used_consistently() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    home = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    styles = (ROOT / "docs" / "stylesheets" / "extra.css").read_text(encoding="utf-8")
    wordmark_path = ROOT / "docs" / "assets" / "images" / "openwfn-wordmark.png"

    assert wordmark_path.exists()
    assert 'src="docs/assets/images/openwfn-wordmark.png"' in readme
    assert 'width="300" alt="openWFN molecular orbital visualization"' in readme
    assert 'alt="openWFN — Wavefunction Analysis"' in readme
    assert "𝕠𝕡𝕖𝕟𝕎𝔽ℕ" not in readme
    assert 'class="ow-brand-lockup"' in home
    assert 'alt="openWFN — Wavefunction Analysis"' in home
    assert "logo: assets/images/openwfn-wordmark.png" in config
    assert ".md-header__button.md-logo img" in styles
    assert 'content: "Wavefunction Analysis"' in styles


def test_python_workflow_uses_real_calculation_accessors() -> None:
    workflow = (ROOT / "docs" / "guides" / "python-workflows.md").read_text(
        encoding="utf-8"
    )

    assert "calculation.molecule.metadata.energy_hartree" in workflow
    assert "calculation.geometry_distance(1, 2)" in workflow
    assert "calculation.geometry_angle(2, 1, 3)" in workflow
    assert "calculation.molecule.formula" not in workflow
    assert "calculation.molecule.coordinates" not in workflow


def test_documentation_covers_required_user_and_scientific_topics() -> None:
    required = (
        "index.md", "installation.md", "quick-start.md", "cli.md", "python-api.md",
        "workbench.md", "formats.md", "methods.md", "validation.md", "limitations.md",
        "citation.md", "tutorials/geometry.md", "tutorials/orbitals-density.md",
        "tutorials/reports.md",
    )
    for relative in required:
        assert (ROOT / "docs" / relative).is_file(), relative


def test_handbook_has_complete_learning_reference_and_project_sections() -> None:
    required = (
        "learn/wavefunction-analysis.md",
        "learn/fchk-anatomy.md",
        "learn/reproducibility.md",
        "guides/cli-workflows.md",
        "guides/python-workflows.md",
        "guides/batch-and-reports.md",
        "guides/troubleshooting.md",
        "reference/cli.md",
        "reference/python-api.md",
        "reference/formats-and-exports.md",
        "science/geometry-topology.md",
        "science/orbitals-density.md",
        "science/population-esp.md",
        "science/validation-status.md",
        "project/security.md",
        "project/contributing.md",
        "project/release-history.md",
    )
    for relative in required:
        assert (ROOT / "docs" / relative).is_file(), relative


def test_cli_reference_covers_every_public_command_family() -> None:
    reference = (ROOT / "docs" / "reference" / "cli.md").read_text(encoding="utf-8")
    commands = (
        "summary", "info", "geometry", "bonds", "graph", "population",
        "orbitals", "density", "esp", "report", "workbench", "cube",
        "convert", "export", "plot", "batch", "validate", "doctor",
        "xyz", "view", "formchk", "interactive",
    )
    for command in commands:
        assert f"`{command}`" in reference, command


def test_security_page_documents_local_processing_and_safe_reporting() -> None:
    security = (ROOT / "docs" / "project" / "security.md").read_text(encoding="utf-8")
    for phrase in ("local", "credentials", "private data", "vulnerability"):
        assert phrase in security.lower()


def test_documented_capability_states_are_defined() -> None:
    validation = (ROOT / "docs" / "validation.md").read_text(encoding="utf-8")
    for state in ("Stable", "Validated", "Experimental", "Unsupported"):
        assert f"**{state}**" in validation


def test_pages_workflow_uses_least_privilege_and_main_only() -> None:
    workflow = (ROOT / ".github" / "workflows" / "docs.yml").read_text(encoding="utf-8")
    assert "branches: [main]" in workflow
    assert "pages: write" in workflow
    assert "id-token: write" in workflow
    assert "contents: read" in workflow
    assert "cancel-in-progress: true" in workflow
    assert "mkdocs build --strict" in workflow
    assert "actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e" in workflow
