import re
import subprocess
import sys
from pathlib import Path

import pytest

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
    stylesheet_entry = "stylesheets/openwfn-site-v2.css"
    stylesheet = ROOT / "docs" / stylesheet_entry

    assert stylesheet_entry in config
    assert '@import url("extra.css?v=20260913");' in stylesheet.read_text(
        encoding="utf-8"
    )
    assert "javascripts/mathjax.js" in config
    assert "cdn.jsdelivr.net/npm/mathjax@3" in config
    assert "navigation.tabs" in config
    assert "navigation.footer" in config


@pytest.mark.docs
def test_homepage_build_has_distinct_title_and_project_favicon(tmp_path: Path) -> None:
    output = tmp_path / "site"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mkdocs",
            "build",
            "--strict",
            "--site-dir",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    homepage = (output / "index.html").read_text(encoding="utf-8")
    assert "<title>Wavefunction analysis - openWFN</title>" in homepage
    assert 'rel="icon" href="assets/images/openwfn-icon.svg"' in homepage
    assert (output / "assets" / "images" / "openwfn-icon.svg").is_file()


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


def test_homepage_contains_product_paths_and_trust_links() -> None:
    home = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")

    for phrase in (
        "Analyze",
        "Automate",
        "Validate",
        "Publish",
        "For researchers",
        "For students",
        "For developers",
        "Validation",
        "Limitations",
        "Citation",
    ):
        assert phrase in home


def test_homepage_uses_documentation_first_product_components() -> None:
    home = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    styles = (ROOT / "docs" / "stylesheets" / "extra.css").read_text(encoding="utf-8")

    for component in (
        "ow-intro", "ow-intro__brand", "ow-intro__command",
        "ow-capability-grid", "ow-terminal", "ow-proof-strip", "ow-support",
    ):
        assert component in home
        assert f".{component}" in styles
    assert "openwfn-orbital-hero.webp" not in home


def test_material_icon_library_and_brand_identity_are_configured() -> None:
    config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")

    assert "logo: assets/images/openwfn-brand.svg" in config
    assert "pymdownx.emoji" in config
    assert "material.extensions.emoji.twemoji" in config
    assert "material.extensions.emoji.to_svg" in config


def test_readme_opens_with_canonical_product_identity() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert '<p align="center">' in readme
    assert 'src="docs/assets/images/openwfn-brand.svg"' in readme
    assert "bgcolor=" not in readme
    assert "Wavefunction analysis, made reproducible." in readme
    assert "openwfn-orbital-hero.webp" not in readme
    assert "openwfn-wordmark.png" not in readme


def test_public_brand_uses_one_canonical_logo() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    home = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    styles = (ROOT / "docs" / "stylesheets" / "extra.css").read_text(encoding="utf-8")

    brand_path = ROOT / "docs" / "assets" / "images" / "openwfn-brand.svg"

    assert brand_path.exists()
    brand = brand_path.read_text(encoding="utf-8")
    assert 'fill="#17213f"' in brand
    assert "data:image/png;base64," in brand
    assert 'src="docs/assets/images/openwfn-brand.svg"' in readme
    assert 'src="assets/images/openwfn-brand.svg"' in home
    assert "logo: assets/images/openwfn-brand.svg" in config
    assert ".md-header__button.md-logo img" in styles
    for obsolete in (
        "openwfn-header.png",
        "openwfn-wordmark.png",
        "openwfn-orbital-hero.webp",
    ):
        assert obsolete not in readme
        assert obsolete not in home


def test_header_has_no_duplicate_plain_title_and_home_identifies_toolkit() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    home = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    styles = (ROOT / "docs" / "stylesheets" / "extra.css").read_text(encoding="utf-8")

    assert ".md-header__topic { display: none; }" in styles
    assert ".md-header__title { display: none; }" not in styles
    product_description = (
        "A unified post-processing toolkit for turning quantum-chemistry "
        "calculations into traceable, reproducible, review-ready results."
    )
    assert product_description in home
    assert product_description in readme


def test_homepage_has_compact_responsive_branding() -> None:
    styles = (ROOT / "docs" / "stylesheets" / "extra.css").read_text(
        encoding="utf-8"
    )

    assert "width: 7.25rem" in styles
    assert "grid-template-columns: minmax(0, 1.12fr) minmax(18rem, 0.88fr)" in styles
    assert "@media (max-width: 44rem)" in styles


def test_site_uses_home_and_five_clear_navigation_groups() -> None:
    config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    nav = config.split("nav:\n", maxsplit=1)[1]
    top_level = re.findall(r"^  - ([^:]+):", nav, flags=re.MULTILINE)

    assert top_level == ["Home", "Get Started", "User Guide", "Reference", "Science", "Project"]


def test_homepage_and_readme_use_generalized_scale_language() -> None:
    public_copy = "\n".join(
        (
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "docs" / "index.md").read_text(encoding="utf-8"),
        )
    ).lower()

    assert "individual calculations and high-throughput collections" in public_copy
    assert not re.search(r"\b(?:1,?000|10,?000)\b", public_copy)


def test_header_uses_compact_asset_and_keeps_mobile_drawer_available() -> None:
    config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    styles = (ROOT / "docs" / "stylesheets" / "extra.css").read_text(
        encoding="utf-8"
    )
    header_logo = ROOT / "docs" / "assets" / "images" / "openwfn-brand.svg"

    assert "logo: assets/images/openwfn-brand.svg" in config
    assert header_logo.exists()
    desktop_media = styles.index("@media (min-width: 60.01rem)")
    drawer_rule = styles.index(
        ".md-main:has(.ow-home) .md-sidebar--primary { display: none; }"
    )
    assert drawer_rule > desktop_media


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


def test_workbench_is_presented_as_optional_and_experimental() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    workbench = (ROOT / "docs" / "workbench.md").read_text(encoding="utf-8")
    quick_start = (ROOT / "docs" / "quick-start.md").read_text(encoding="utf-8")
    metadata = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "| Research reports |" in readme
    assert "| Interactive workbench |" in readme
    assert "| Interactive workbench | Optional visualization" in readme
    assert "Experimental" in workbench
    assert "not a numerical reference" in workbench
    assert "workbench" not in quick_start.lower()
    assert "offline workbench" not in metadata.lower()


def test_pages_workflow_uses_least_privilege_and_main_only() -> None:
    workflow = (ROOT / ".github" / "workflows" / "docs.yml").read_text(encoding="utf-8")
    assert "branches: [main]" in workflow
    assert "pages: write" in workflow
    assert "id-token: write" in workflow
    assert "contents: read" in workflow
    assert "cancel-in-progress: true" in workflow
    assert "mkdocs build --strict" in workflow
    assert "actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e" in workflow


def test_mkdocs_integration_test_runs_only_in_documentation_workflow() -> None:
    test_workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
        encoding="utf-8"
    )
    docs_workflow = (ROOT / ".github" / "workflows" / "docs.yml").read_text(
        encoding="utf-8"
    )
    config = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"docs: tests that require the documentation toolchain"' in config
    assert 'python -m pytest --strict-markers -m "not docs"' in test_workflow
    assert "python -m pip install .[test,docs]" in docs_workflow
    assert "python -m pytest --strict-markers -m docs tests/docs" in docs_workflow
