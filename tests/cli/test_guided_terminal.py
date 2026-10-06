"""Real pseudo-terminal replays, not mocked keyboard input."""

import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.name == 'nt', reason='POSIX pseudo-terminal replay')
ROOT = Path(__file__).resolve().parents[2]


def test_terminal_arrows_enter_escape_and_ctrl_c():
    pexpect = pytest.importorskip('pexpect')
    child = pexpect.spawn(sys.executable, ['-m', 'openwfn.cli',
                          str(ROOT / 'examples/water/water.fchk'), 'open'],
                          cwd=str(ROOT), encoding='utf-8', timeout=12, dimensions=(24, 80))
    try:
        child.expect('Select a workflow')
        child.send('\x1b[B\x1b[A\r')  # Down, Up, Enter: overview
        child.expect('Molecular Summary')
        child.expect('Result actions:')
        child.send('\x1b')  # Escape: home
        child.expect('Select a workflow')
        child.sendcontrol('c')
        child.expect(pexpect.EOF)
        child.close()
        assert child.exitstatus == 0
        assert 'Traceback' not in child.before
    finally:
        child.close(force=True)


def test_terminal_parameter_delete_cannot_reach_density():
    pexpect = pytest.importorskip('pexpect')
    child = pexpect.spawn(sys.executable, ['-m', 'openwfn.cli',
                          str(ROOT / 'examples/water/water.fchk'), 'open'],
                          cwd=str(ROOT), encoding='utf-8', timeout=12, dimensions=(24, 80))
    try:
        child.expect('Select a workflow')
        child.send('\x1b[B' * 6 + '\r')  # Density family
        child.expect('Density operation')
        child.send('\x1b[3~')  # Delete must not become a density-kind string
        child.send('\x1b')
        child.expect('Result actions:|Select a workflow')
        child.sendcontrol('c')
        child.expect(['Select a workflow', pexpect.EOF], timeout=12)
    finally:
        child.close(force=True)


def test_terminal_no_file_backspace_and_eof(tmp_path):
    pexpect = pytest.importorskip('pexpect')
    source = tmp_path / 'water β.molden.input'
    source.write_bytes((ROOT / 'tests/fixtures/interop/molden/water.molden').read_bytes())
    child = pexpect.spawn(sys.executable, ['-m', 'openwfn.cli'],
                          cwd=str(tmp_path), encoding='utf-8', timeout=12, dimensions=(24, 80))
    try:
        child.expect('Input file')
        child.send(str(source) + 'x\x7f\r')  # Correct a filename using Backspace
        child.expect('Select a workflow')
        child.sendcontrol('d')  # EOF must exit, not be discarded by raw mode
        child.expect(pexpect.EOF)
        child.close()
        assert child.exitstatus == 0
        assert not (tmp_path / 'results').exists()
    finally:
        child.close(force=True)
