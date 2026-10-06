"""Pinned external point evidence; does not promote basin validation status."""
import hashlib
import json
from pathlib import Path

import numpy as np

from openwfn.analysis.realspace import evaluate_density_fields, evaluate_density_gradient
from openwfn.api import load
from openwfn.constants import BOHR_TO_ANGSTROM

ROOT = Path(__file__).resolve().parents[2]


def test_density_derivatives_agree_with_independently_executed_critic2():
    evidence = json.loads((ROOT / 'tests/reference_data/critic2_methane_density_points.json').read_text())
    source = ROOT / evidence['input']
    assert hashlib.sha256(source.read_bytes()).hexdigest() == evidence['input_sha256']
    transcript = ROOT / 'validation/qtaim-basins/investigation/critic2-methane-points.out'
    assert hashlib.sha256(transcript.read_bytes()).hexdigest() == evidence['transcript_sha256']
    points = np.asarray([p['coordinates_angstrom'] for p in evidence['points']]) / BOHR_TO_ANGSTROM
    data = load(source).data.calculation
    full = evaluate_density_fields(data, points)
    rho, gradient = evaluate_density_gradient(data, points)
    tolerance = evidence['absolute_tolerance']
    for actual, expected in ((full.rho, [p['rho'] for p in evidence['points']]),
                             (full.gradient, [p['gradient'] for p in evidence['points']]),
                             (full.laplacian, [p['laplacian'] for p in evidence['points']])):
        np.testing.assert_allclose(actual, expected, rtol=0, atol=tolerance)
    np.testing.assert_allclose(rho, full.rho, rtol=0, atol=1e-14)
    np.testing.assert_allclose(gradient, full.gradient, rtol=0, atol=1e-14)
