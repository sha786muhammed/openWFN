import io
import os

from openwfn.app import CommandContext, execute
from openwfn.results import ResultRecord


def test_output_hardlink_cannot_replace_input(tmp_path):
    source = tmp_path / 'input.fchk'
    source.write_text('original input')
    destination = tmp_path / 'alias.json'
    os.link(source, destination)
    context = CommandContext(input_path=source, output_path=destination, overwrite=True,
                             error_stream=io.StringIO(), output_stream=io.StringIO())
    assert execute(lambda: ResultRecord('summary', {'charge': 0}), context) != 0
    assert source.read_text() == 'original input'
    assert 'input' in context.error_stream.getvalue().lower()


def test_failed_output_write_preserves_existing_file(tmp_path, monkeypatch):
    from pathlib import Path
    destination = tmp_path / 'record.json'
    destination.write_text('original result')
    original = Path.write_text
    def interrupted(path, text, **kwargs):
        original(path, 'partial', **kwargs)
        raise OSError('disk full')
    monkeypatch.setattr(Path, 'write_text', interrupted)
    context = CommandContext(output_path=destination, overwrite=True, format='json',
                             error_stream=io.StringIO(), output_stream=io.StringIO())
    assert execute(lambda: ResultRecord('summary', {'charge': 0}), context) != 0
    assert destination.read_text() == 'original result'
    assert list(tmp_path.iterdir()) == [destination]
