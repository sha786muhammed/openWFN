#!/usr/bin/env python3
"""Optional pinned real-log checks; source log redistribution is not assumed."""
import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
COMMIT = '127b2229d584d54fb84a74e383edb18a271fc283'
SOURCES = {'gaussian': 'Gaussian/Gaussian09/water_gaussian.inp.log',
           'orca': 'ORCA/ORCA4.2/water_mp2.out'}
HASHES = {'gaussian': 'b53efef3938561ea060a2b218beb46650fff5fc085c758359a941717952fd850',
          'orca': '666f71fd4c04d73ac1872934382979e5a230aab18365fa28415ddf65b5293061'}


def main():
    from openwfn.output_properties import read_output
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--download', action='store_true', help='Fetch the two explicitly pinned public reference logs')
    args = parser.parse_args()
    args.input_dir.mkdir(parents=True, exist_ok=True)
    cases = []
    for name, relative in SOURCES.items():
        url = f'https://raw.githubusercontent.com/cclib/cclib-data/{COMMIT}/{relative}'
        path = args.input_dir/f'{name}.txt'
        if args.download:
            with urllib.request.urlopen(url, timeout=30) as response:
                content = response.read(1_000_001)
            if len(content) > 1_000_000:
                raise ValueError('Pinned reference exceeds size bound')
            path.write_bytes(content)
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != HASHES[name]:
            raise ValueError(f'{name}: reference checksum mismatch')
        text = content.decode()
        record = read_output(path)
        assert record.data['atom_count'] == 3
        assert record.data['charge'] == 0
        assert record.data['multiplicity'] == 1
        if name == 'orca':
            printed = float(re.findall(r'Total Energy\s*:\s*([-\d.]+) Eh', text)[-1])
            assert abs(record.data['scf_energy_hartree']-printed) < 1e-8
            block = text.split('MULLIKEN ATOMIC CHARGES\n', 1)[1].split('Sum of atomic charges:', 1)[0]
            charges = [float(value) for value in re.findall(r'\d+\s+[A-Z][a-z]?\s*:\s*([-\d.]+)', block)]
            assert np.max(np.abs(np.array(record.data['reported_atomic_charges']['mulliken']['charges'])-charges)) < 1e-6
            magnitude = float(re.findall(r'Magnitude \(Debye\)\s*:\s*([-\d.]+)', text)[-1])
            assert abs(np.linalg.norm(record.data['dipole_debye'])-magnitude) < 5e-5
            energy_evidence = {'printed_scf_energy_hartree': printed, 'tolerance': 1e-8,
                               'printed_mulliken_charges': charges, 'charge_tolerance': 1e-6,
                               'printed_dipole_magnitude_debye': magnitude, 'dipole_tolerance': 5e-5}
        else:
            # This is a genuine CASSCF-only output, not an SCF source. It is an
            # important negative example: do not relabel its energy as SCF.
            assert 'CASSCF' in text and 'SCF Done:' not in text
            assert record.data['scf_energy_hartree'] is None
            assert record.status == 'partial'
            assert any('No SCF energy' in warning for warning in record.warnings)
            energy_evidence = {'expected_scf_energy_hartree': None, 'reason': 'CASSCF-only job'}
        cases.append({'source_url': url, 'upstream_commit': COMMIT,
                      'input_sha256': hashlib.sha256(content).hexdigest(),
                      'program': name, 'energy_evidence': energy_evidence,
                      'result': record.as_dict(), 'validation_status': 'Experimental',
                      'scope': 'Printed SCF energy, ORCA Mulliken charges/dipole magnitude, atom count, charge/multiplicity and genuine absent-SCF behavior. Other parsed fields are observations, not independently validated.'})
    report = {'status': 'passed', 'cases': cases,
              'redistribution': 'Numeric evidence only. Upstream log licensing was not established; source logs are fetched explicitly and are not redistributed here.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print('Two real output-reader cases passed')


if __name__ == '__main__':
    main()
