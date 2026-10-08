"""Exercise actual terminal keys without a paid or downloaded model."""

import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='POSIX PTY test')
ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'src/openwfn/example_data/everyday-qc/ethanol.molden'


def test_chat_keys_cancel_open_query_close_disconnect_and_exit():
    pexpect = pytest.importorskip('pexpect')
    environment = os.environ.copy()
    environment.pop('OPENWFN_CHAT_MODEL', None)
    environment.pop('OPENWFN_CHAT_ENDPOINT', None)
    environment['TERM'] = 'xterm-256color'
    environment['PROMPT_TOOLKIT_NO_CPR'] = '1'
    child = pexpect.spawn(sys.executable, ['-m', 'openwfn.cli', 'chat'], cwd=ROOT,
                          env=environment, encoding='utf-8', timeout=15, dimensions=(24, 80))
    try:
        child.expect('No file open')
        child.expect('›')
        child.sendcontrol('c')
        child.expect('Cancelled')
        child.sendline('/connect')
        child.expect('Connect a model')
        child.send('\x1b')
        child.expect('›')
        child.sendline('/open ' + str(SOURCE))
        child.expect('Opened:')
        child.sendline('What is the HOMO energy?')
        child.expect(r'-0\.331537655 Hartree')
        child.sendline('/close')
        child.expect('File closed')
        child.sendline('/record')
        child.expect('input_sha256')
        child.sendline('/disconnect')
        child.expect('Disconnected')
        child.sendline('/quit')
        child.expect(pexpect.EOF)
        child.close()
        assert child.exitstatus == 0
    finally:
        if child.isalive():
            child.terminate(force=True)


def test_model_picker_filters_and_selects_with_arrow_keys():
    pexpect = pytest.importorskip('pexpect')
    code = "from openwfn.assistant_terminal import _choose; print('selected=' + str(_choose('Choose model', ['alpha-model', 'beta-model'])))"
    environment = {**os.environ, 'TERM': 'xterm-256color', 'PROMPT_TOOLKIT_NO_CPR': '1'}
    child = pexpect.spawn(sys.executable, ['-c', code], cwd=ROOT, env=environment,
                          encoding='utf-8', timeout=15)
    try:
        child.expect('Choose model')
        child.send('beta')
        child.sendline('')
        child.expect('selected=beta-model')
        child.expect(pexpect.EOF)
        child.close()
        assert child.exitstatus == 0
    finally:
        if child.isalive():
            child.terminate(force=True)


def test_ctrl_c_cancels_pending_density_choice():
    pexpect = pytest.importorskip('pexpect')
    environment = os.environ.copy()
    environment.pop('OPENWFN_CHAT_MODEL', None)
    environment.pop('OPENWFN_CHAT_ENDPOINT', None)
    environment.update(TERM='xterm-256color', PROMPT_TOOLKIT_NO_CPR='1')
    child = pexpect.spawn(sys.executable, ['-m', 'openwfn.cli', str(SOURCE), 'chat'],
                          cwd=ROOT, env=environment, encoding='utf-8', timeout=15)
    try:
        child.expect('›')
        child.sendline('total density')
        child.expect('Reply integrate, cube, or point')
        child.sendcontrol('c')
        child.expect('Cancelled')
        child.sendline('integrate')
        child.expect('Use /connect')
        child.sendline('/quit')
        child.expect(pexpect.EOF)
        child.close()
        assert child.exitstatus == 0
    finally:
        if child.isalive():
            child.terminate(force=True)
