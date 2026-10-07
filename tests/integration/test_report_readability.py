import json
import re
from pathlib import Path

import pytest

from openwfn.ingest import load_input
from openwfn.reporting import build_report

ROOT = Path(__file__).resolve().parents[2]
ETHANOL = ROOT / 'src/openwfn/example_data/everyday-qc/ethanol.molden'


def test_html_population_labels_keep_atom_order_and_raw_values(tmp_path):
    output = tmp_path / 'report.html'
    build_report(load_input(ETHANOL), ('mulliken', 'lowdin'), output, 'html', 'test', {})
    text = output.read_text()
    visible = text.split('<script id="openwfn-report"')[0]
    assert '<th>Element</th>' in visible
    assert re.search(r'<td>3</td>\s*<td>O</td>\s*<td>8\.33969457</td>\s*<td>-0\.33969457</td>', visible)
    assert re.search(r'<td>9</td>\s*<td>H</td>\s*<td>0\.86288215</td>\s*<td>0\.13711785</td>', visible)
    assert 'Atomic Charges</th><td>[' not in visible
    payload = text.split('type="application/json">')[1].split('</script>')[0]
    assert json.loads(payload)['sections'][0]['data']['atomic_charges'][2] == pytest.approx(-.33969457)


@pytest.mark.parametrize('report_format,suffix', [('html', '.html'), ('markdown', '.md')])
def test_report_displays_missing_values_without_changing_unknown_state(tmp_path, report_format, suffix):
    source = tmp_path / 'atom.xyz'
    source.write_text('1\natom\nHe 0 0 0\n')
    output = tmp_path / ('report' + suffix)
    build_report(load_input(source), ('summary',), output, report_format, 'test', {})
    visible = output.read_text().split('<script id="openwfn-report"')[0]
    assert 'Not available' in visible
    assert 'None' not in visible


def test_markdown_population_tables_are_labelled(tmp_path):
    output = tmp_path / 'report.md'
    build_report(load_input(ETHANOL), ('mulliken',), output, 'markdown', 'test', {})
    text = output.read_text()
    assert '| Atom | Element | Electron population (electron) | Charge (e) |' in text
    assert '| 3 | O | 8.33969457 | -0.33969457 |' in text
    assert 'Atomic Charges: [' not in text
