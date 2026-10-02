"""Bounded real-example CLI benchmarks; optional openwfn[resources] extra."""
import argparse
import hashlib
import json
import os
import platform
import sys
import tempfile
from pathlib import Path

from openwfn.resource_budget import run_resource_command


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--timeout', default=120., type=float)
    parser.add_argument('--ram-mib', default=1024, type=int)
    parser.add_argument('--output-mib', default=128, type=int)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    executable = str(Path(sys.executable).with_name('openwfn'))
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    records = []
    source_hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (root/'src/openwfn').rglob('*.py')}
    with tempfile.TemporaryDirectory(prefix='openwfn-resources-') as temporary:
        for source in sorted((root/'examples/everyday-qc').glob('*.molden')):
            molecule = source.stem
            workflows = {
                'geometry': ['summary'],
                'mayer': ['bondorder', 'mayer'],
                'dos': ['orbitals', 'dos', '--spin', 'all', '--export', 'dos.csv'],
                'pdos': ['orbitals', 'pdos', '--spin', 'all', '--export', 'pdos.csv'],
                'density_cube': ['density', 'cube', 'density.cube', '--spacing', '.5', '--padding', '3'],
                'mo_cube': ['orbitals', 'cube', '--mo', 'homo', '--output', 'homo.cube', '--spacing', '.5', '--padding', '3'],
                'workbench': ['workbench', 'workbench.html'],
                'esp': ['esp', 'point', '4', '3', '2', '--component', 'electronic'],
                'report': ['report', 'build', 'report.html', '--analyses', 'summary,mayer,dos,pdos'],
            }
            for name, arguments in workflows.items():
                folder = Path(temporary)/molecule/name
                result = run_resource_command([executable, str(source), *arguments], folder,
                    timeout_seconds=args.timeout, max_rss_bytes=args.ram_mib*1024**2,
                    max_output_bytes=args.output_mib*1024**2, env=env)
                result.update(molecule=molecule, workflow=name,
                    input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    artifacts={p.name: {'bytes': p.stat().st_size,
                        'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                        for p in folder.iterdir() if p.is_file()})
                # Temporary paths do not survive the benchmark; retain hashes.
                result.pop('stdout_path')
                result.pop('stderr_path')
                records.append(result)
    report = {'python': platform.python_version(), 'platform': platform.platform(),
        'threads': 1, 'source_sha256': source_hashes, 'records': records,
        'limitations': ['Sampled RSS can miss short-lived peaks.',
            'Disk and RAM limits are monitored, not OS hard quotas.',
            'Very short-lived detached children can evade sampling; use trusted commands.',
            'These prescribed geometries are examples, not optimized structures.',
            'Resource success does not establish scientific validation.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    return 0 if all(r['status'] == 'success' for r in records) else 1


if __name__ == '__main__':
    raise SystemExit(main())
