#!/usr/bin/env python3
"""Run an offline Chromium workbench check against real molecular/API values.

Requires optional validation dependencies playwright and qc-iodata. This tests
browser execution, workspace/surface controls, measurement callback and readout;
it does not certify GPU vendors or the accuracy of a coarse preview grid.
"""
import argparse
import json
from pathlib import Path

from openwfn.api import load
from openwfn.workbench.export import export_workbench

ROOT = Path(__file__).resolve().parents[1]


def validate_case(browser, name, output):
    calc = load(ROOT/f'examples/everyday-qc/{name}.molden')
    path = export_workbench(calc.data.calculation, output/f'{name}.html')
    page = browser.new_page(viewport={'width': 1400, 'height': 900})
    errors, network = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: network.append(request.url) if request.url.startswith(('http:', 'https:')) else None)
    page.route('http://**/*', lambda route: route.abort())
    page.route('https://**/*', lambda route: route.abort())
    page.goto(path.resolve().as_uri())
    page.wait_for_selector('#viewer canvas')
    fields = page.evaluate('payload.fields.map(f=>({id:f.id,status:f.status,validation_status:f.validation_status,warnings:f.warnings||[]}))')
    for workspace in ('structure', 'orbitals', 'density', 'esp', 'measurements'):
        page.locator(f'[data-workspace="{workspace}"]').click()
        assert f'{workspace.title()} workspace' in page.locator('#status-line').inner_text()
        if workspace in ('orbitals', 'density', 'esp'):
            options = page.locator('#field-select option').count()
            for index in range(options):
                page.locator('#field-select').select_option(index=index)
                assert page.locator('#surface-metadata').inner_text()
                page.locator('#isovalue').fill('0.025')
                page.locator('#isovalue').dispatch_event('input')
    measurements = []
    definitions = [('distance', (1, 2), calc.geometry_distance)]
    if len(calc.molecule.atoms) >= 3:
        definitions.append(('angle', (2, 1, 3), calc.geometry_angle))
    if name == 'ethanol':
        definitions.append(('dihedral', (4, 1, 2, 3), calc.geometry_dihedral))
    for kind, indices, operation in definitions:
        page.locator(f'[data-measurement="{kind}"]').click()
        # Exercise the same callback registered with the 3Dmol atom-picking API.
        for index in indices:
            page.evaluate('(index)=>selectMeasurementAtom(index)', index-1)
        text = page.locator('#measurement-result').inner_text()
        actual = float(text.split()[0])
        expected = operation(*indices).data['value']
        assert abs(actual-expected) <= 1e-6, (name, kind, text, expected)
        measurements.append({'kind': kind, 'atom_indices': indices, 'display': text,
                             'reference': expected, 'absolute_error': abs(actual-expected)})
        page.locator('#measurement-reset').click()
        assert page.locator('#measurement-selection').inner_text() == 'None'
    page.screenshot(path=str(output/f'{name}.png'))
    assert not errors, errors
    assert not network, network
    page.close()
    return {'case': name, 'status': 'passed', 'workspaces': 5, 'measurements': measurements,
            'fields': fields, 'javascript_errors': errors, 'network_requests': network,
            'input_sha256': calc.data.provenance.sha256}


def main():
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('/tmp/openwfn-browser-validation'))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(args=['--enable-unsafe-swiftshader'])
        report = {'status': 'passed', 'browser': browser.version,
                  'scope': 'offline Chromium; workspace/surface controls and atom-selection callback; API geometry parity',
                  'cases': [validate_case(browser, name, args.output_dir)
                            for name in ('water', 'oxygen_triplet', 'ammonium_cation', 'ethanol')]}
        browser.close()
    (args.output_dir/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(f"{len(report['cases'])} real-molecule browser workflows passed")


if __name__ == '__main__':
    main()
