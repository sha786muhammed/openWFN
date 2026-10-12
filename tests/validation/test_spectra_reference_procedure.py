import importlib.util


def test_printed_reference_retains_negative_frequency_and_zero_strength():
    assert importlib.util.find_spec('scripts.validate_spectra_references'), 'Spectra reference procedure missing'
    from scripts.validate_spectra_references import printed_vibrations
    values = printed_vibrations(''' Frequencies -- -512.25 1000.0 2000.0
 IR Inten -- 10.0 0.0 20.0
 Raman Activ -- 0.0 3.0 4.0
''', 'gaussian')
    assert values['frequencies'] == [-512.25, 1000., 2000.]
    assert values['ir'] == [10., 0., 20.]
    assert values['raman'] == [0., 3., 4.]
