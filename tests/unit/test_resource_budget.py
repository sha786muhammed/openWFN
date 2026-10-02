"""Real subprocess resource behavior; no timing-only happy-path claims."""
import sys

import pytest


def run(tmp_path, code, **limits):
    pytest.importorskip('psutil')
    from openwfn.resource_budget import run_resource_command

    return run_resource_command([sys.executable, '-c', code], tmp_path,
                                timeout_seconds=limits.get('timeout_seconds', 3.),
                                max_rss_bytes=limits.get('max_rss_bytes', 128*1024**2),
                                max_output_bytes=limits.get('max_output_bytes', 1024**2))


def test_success_has_observed_rss_and_bounded_capture(tmp_path):
    result = run(tmp_path, "import time; print('real result'); time.sleep(.1)")
    assert result['status'] == 'success'
    assert result['peak_observed_rss_bytes'] > 0
    assert result['output_bytes'] >= len('real result\n')
    assert (tmp_path/'stdout.log').read_text() == 'real result\n'


def test_timeout_terminates_work(tmp_path):
    result = run(tmp_path, 'import time; time.sleep(30)', timeout_seconds=.15)
    assert result['status'] == 'timeout'
    assert result['elapsed_seconds'] < 3.


def test_memory_limit_terminates_large_allocation(tmp_path):
    result = run(tmp_path, 'import time; x=bytearray(80*1024**2); time.sleep(10)', max_rss_bytes=32*1024**2)
    assert result['status'] == 'memory_limit'
    assert result['peak_observed_rss_bytes'] > 32*1024**2


def test_output_limit_includes_files_and_stdout(tmp_path):
    result = run(tmp_path, "from pathlib import Path; Path('large.bin').write_bytes(b'x'*65536)", max_output_bytes=4096)
    assert result['status'] == 'output_limit'
    assert result['output_bytes'] > 4096


@pytest.mark.parametrize('limit', [0, -1, float('nan'), float('inf')])
def test_invalid_budgets_fail_before_execution(tmp_path, limit):
    with pytest.raises(ValueError):
        run(tmp_path, "raise RuntimeError('must never start')", timeout_seconds=limit)


def test_failed_process_is_reported(tmp_path):
    result = run(tmp_path, "raise RuntimeError('expected failure')")
    assert result['status'] == 'process_error'
    assert result['returncode'] != 0
    assert 'expected failure' in (tmp_path/'stderr.log').read_text()


def test_timeout_stops_descendant_writes(tmp_path):
    import time

    child = "from pathlib import Path; import time; time.sleep(.7); Path('escaped').write_text('bad')"
    code = f'import subprocess, sys, time; subprocess.Popen([sys.executable, "-c", {child!r}]); time.sleep(30)'
    result = run(tmp_path, code, timeout_seconds=.15)
    assert result['status'] == 'timeout'
    time.sleep(.8)
    assert not (tmp_path/'escaped').exists()


@pytest.mark.skipif(sys.platform == 'win32', reason='POSIX session behavior')
def test_timeout_stops_child_in_separate_session(tmp_path):
    import time

    child = "from pathlib import Path; import time; time.sleep(.7); Path('escaped').write_text('bad')"
    code = f'import subprocess, sys, time; subprocess.Popen([sys.executable, "-c", {child!r}], start_new_session=True); time.sleep(30)'
    result = run(tmp_path, code, timeout_seconds=.15)
    assert result['status'] == 'timeout'
    time.sleep(.8)
    assert not (tmp_path/'escaped').exists()


def test_parent_exit_cannot_leave_child_writing_after_return(tmp_path):
    import time

    child = "from pathlib import Path; import time; time.sleep(.7); Path('escaped').write_text('bad')"
    code = f'import subprocess, sys, time; subprocess.Popen([sys.executable, "-c", {child!r}]); time.sleep(.05)'
    result = run(tmp_path, code)
    assert result['status'] == 'process_error'
    time.sleep(.8)
    assert not (tmp_path/'escaped').exists()


def test_disk_preflight_rejects_before_start(tmp_path, monkeypatch):
    import shutil

    monkeypatch.setattr(shutil, 'disk_usage', lambda _: shutil._ntuple_diskusage(100, 99, 1))
    with pytest.raises(ValueError, match='free disk'):
        run(tmp_path, "from pathlib import Path; Path('started').touch()")
    assert not (tmp_path/'started').exists()


def test_existing_logs_are_preserved(tmp_path):
    (tmp_path/'stdout.log').write_text('previous record')
    with pytest.raises(FileExistsError):
        run(tmp_path, "print('must not replace')")
    assert (tmp_path/'stdout.log').read_text() == 'previous record'


def test_short_commands_preserve_results_without_inventing_rss(tmp_path):
    result = run(tmp_path, "print('short result')")
    assert result['returncode'] == 0
    assert result['status'] in {'success', 'measurement_unavailable'}
    assert (tmp_path/'stdout.log').read_text() == 'short result\n'
    if result['status'] == 'measurement_unavailable':
        assert result['peak_observed_rss_bytes'] == 0
    else:
        assert result['peak_observed_rss_bytes'] > 0
