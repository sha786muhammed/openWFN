"""Editable scrollback-friendly terminal chat input; no persisted history."""

import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

COMMANDS = ['/connect', '/model', '/models', '/disconnect', '/open', '/close', '/inspect',
            '/details', '/record', '/save', '/clear', '/help', '/quit']


class ChatInput:
    def __init__(self):
        from .utils import color_enabled
        self.session = None
        if sys.stdin.isatty() and sys.stdout.isatty():
            bindings = KeyBindings()
            @bindings.add('enter')
            def send(event):
                event.current_buffer.validate_and_handle()
            @bindings.add('escape', 'enter')
            def newline(event):
                event.current_buffer.insert_text('\n')
            self.session = PromptSession(history=InMemoryHistory(),
                completer=WordCompleter(COMMANDS), key_bindings=bindings,
                style=Style.from_dict({'prompt': 'ansicyan bold', 'bottom-toolbar': 'ansibrightblack'}
                                     if color_enabled() else {}))

    def prompt(self):
        if self.session is None:
            return input('› ')
        return self.session.prompt([('class:prompt', '› ')], multiline=True,
            bottom_toolbar='/open  /model  /save  /details · Enter send · Alt+Enter newline')
