"""Tabular and publication-style export of shared spectrum ResultRecords."""
import csv
import json
from pathlib import Path

from ..results import ResultRecord
from .tables import ExportRequest


def write_spectrum(result: ResultRecord, path: str | Path, *, overwrite: bool = False,
                   dpi: int = 300) -> Path:
    if result.status == 'failed' or result.kind not in {'orbital_dos', 'orbital_pdos'}:
        raise ValueError('spectrum export requires a usable orbital DOS/PDOS result')
    path = Path(path)
    request = ExportRequest(path, path.suffix.lstrip('.'), overwrite, dpi)
    if path.suffix.lower() not in {'.csv', '.json', '.png', '.svg'}:
        raise ValueError('spectrum supports CSV, JSON, PNG or SVG')
    request.ensure_writable()
    series = {'total_dos': result.data['total_dos'], **result.data['channels'],
              **result.data.get('projections', {})}
    energy = result.data['energy_ev']
    if path.suffix.lower() == '.json':
        path.write_text(json.dumps(result.as_dict(), indent=2)+'\n', encoding='utf-8')
    elif path.suffix.lower() == '.csv':
        with path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['energy_ev', *series])
            for i, value in enumerate(energy):
                writer.writerow([value, *(values[i] for values in series.values())])
    else:
        from matplotlib.figure import Figure

        figure = Figure(figsize=(6.4, 4.2), layout='constrained')
        axis = figure.subplots()
        for label, values in series.items():
            axis.plot(energy, values, lw=1.3, label=label)
        axis.set(xlabel='Orbital energy (eV)', ylabel='Orbital DOS (orbitals/eV)')
        axis.spines[['top', 'right']].set_visible(False)
        if len(series) <= 12:
            axis.legend(frameon=False, fontsize=8)
        axis.tick_params(direction='in')
        axis.margins(x=0)
        metadata = {'Description': json.dumps({'analysis': result.analysis_name, 'validation_status': result.validation_status,
                    'warnings': result.warnings, 'provenance': result.provenance}, sort_keys=True)} if path.suffix.lower() == '.svg' else None
        figure.savefig(path, dpi=dpi, metadata=metadata)
        figure.clear()
    return path
