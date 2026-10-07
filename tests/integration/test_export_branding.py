"""Offline scientific exports carry the same public identity without network assets."""

from pathlib import Path

from openwfn.branding import wordmark_svg
from openwfn.model import CalculationData
from openwfn.reporting import _html
from openwfn.workbench.export import export_workbench


def test_research_html_embeds_canonical_wordmark():
    document = _html({'sections': [], 'generated_at': 'test', 'openwfn_version': 'test',
                      'input': {'sha256': 'test'}, 'command': 'test'})
    assert wordmark_svg().strip() in document


def test_offline_workbench_embeds_canonical_wordmark(tmp_path):
    from openwfn import load

    source = Path(__file__).resolve().parents[2] / 'src/openwfn/example_data/everyday-qc/ethanol.molden'
    calculation = load(source)
    assert isinstance(calculation.data.calculation, CalculationData)
    output = export_workbench(calculation.data.calculation, tmp_path / 'workbench.html')
    assert wordmark_svg().strip() in output.read_text(encoding='utf-8')


def test_custom_title_is_not_interpreted_as_a_brand_placeholder(tmp_path):
    from openwfn import load
    source = Path(__file__).resolve().parents[2] / 'src/openwfn/example_data/everyday-qc/ethanol.molden'
    output = export_workbench(load(source).data.calculation, tmp_path / 'workbench.html', title='__BRAND__')
    assert '<title>__BRAND__</title>' in output.read_text(encoding='utf-8')
