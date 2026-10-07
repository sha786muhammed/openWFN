"""Editable scrollback-friendly terminal chat input; no persisted history."""

import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings

COMMANDS = ['/connect', '/models', '/disconnect', '/open', '/close', '/inspect',
            '/record', '/save', '/clear', '/help', '/quit']


class ChatInput:
    def __init__(self):
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
                completer=WordCompleter(COMMANDS), key_bindings=bindings)

    def prompt(self):
        if self.session is None:
            return input('› ')
        return self.session.prompt('› ', multiline=True,
            bottom_toolbar='Enter send · Alt+Enter newline · /help commands')
