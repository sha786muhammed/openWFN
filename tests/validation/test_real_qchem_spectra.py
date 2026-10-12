import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from openwfn.analysis.registry import run_analysis_safe
from openwfn.api import load


def test_real_qchem_ir_matches_printed_modes_and_independent_broadening():
    iodata = pytest.importorskip('iodata')
    source = Path(iodata.__file__).parent / 'test/data/water_hf_ccpvtz_freq_qchem.out'
    if not source.is_file():
        pytest.skip('Installed IOData package does not include the real Q-Chem fixture')
    # Printed Frequency and IR Intens lines in this source, not openWFN output.
    frequencies = np.array([1806.46, 3908.95, 3995.00])
    strengths = np.array([86.773, 13.894, 67.097])
    calculation = load(source)
    modes = calculation.analyze('vibrations')
    np.testing.assert_allclose([mode['frequency_cm1'] for mode in modes.data['modes']], frequencies,
                               rtol=0, atol=1e-8)
    np.testing.assert_allclose([mode['ir_intensity_km_mol'] for mode in modes.data['modes']], strengths,
                               rtol=0, atol=1e-8)
    spectrum = calculation.analyze('ir-spectrum', fwhm_cm1=20.)
    grid = np.asarray(spectrum.data['frequency_cm1'])
    reference = np.sum(strengths * np.exp(-4 * np.log(2) *
                       ((grid[:, None] - frequencies) / 20.) ** 2), axis=1)
    np.testing.assert_allclose(spectrum.data['intensity'], reference, rtol=0, atol=1e-8)
    command = subprocess.run([sys.executable, '-m', 'openwfn.cli', '--format', 'json',
                              str(source), 'spectra', 'ir', '--fwhm', '20'],
                             capture_output=True, text=True, check=True)
    payload = json.loads(command.stdout)
    assert payload['data'] == spectrum.data
    assert payload['warnings'] == list(spectrum.warnings)
    assert payload['provenance']['input_sha256'] == 'cc69bca032718c3c9982a361eae6a3812ac225d5e070f45110d57bb8312a09ac'
    # "Raman Active: YES" alone is not a numerical Raman activity.
    raman = run_analysis_safe(calculation.data, 'raman-spectrum')
    assert raman.status == 'failed'
    assert raman.error.category == 'DataUnavailableError'
