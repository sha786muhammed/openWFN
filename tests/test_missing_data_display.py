import csv
import io
import json

from openwfn.app import CommandContext
from openwfn.errors import DataUnavailableError, ParseError
from openwfn.presentation import render
from openwfn.results import ResultRecord


def failure(exception):
    return ResultRecord.failure(kind='vibrational_spectrum', analysis_name='ir-spectrum',
                                analysis_version='1', exception=exception, elapsed_seconds=0)


def test_missing_records_are_explained_without_relabelling_corrupt_inputs():
    missing = failure(DataUnavailableError('Requires vibrational frequencies and IR intensities.'))
    text = render(missing, CommandContext(format='plain', compact=True))
    assert 'Not available from this file.' in text
    assert 'vibrational frequencies and IR intensities' in text
    assert 'Error:' not in text
    corrupted = render(failure(ParseError('Truncated input.')), CommandContext(format='plain', compact=True))
    assert 'Not available from this file.' not in corrupted
    assert 'Error: Truncated input.' in corrupted
    assert json.loads(render(missing, CommandContext(format='json', compact=True)))['status'] == 'failed'


def test_failed_csv_keeps_failure_reason_instead_of_an_empty_spectrum():
    missing = failure(DataUnavailableError('IR intensities are absent.'))
    rows = list(csv.DictReader(io.StringIO(render(missing, CommandContext(format='csv')))))
    assert len(rows) == 1
    assert rows[0]['status'] == 'failed'
    assert rows[0]['error_message'] == 'IR intensities are absent.'
    assert rows[0]['analysis_name'] == 'ir-spectrum'
