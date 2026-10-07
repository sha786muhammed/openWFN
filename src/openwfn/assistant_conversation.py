"""Optional file/model state without weakening file-bound scientific execution."""

import json
import re

from .assistant import AssistantAnswer, AssistantSession, _direct_plan
from .assistant_connections import ModelConnection
from .assistant_help import local_help
from .assistant_intents import resolve_intent
from .assistant_model import LocalModel


class ConversationSession:
    def __init__(self, file_session: AssistantSession | None = None,
                 model: LocalModel | None = None):
        self.file_session = file_session
        self.connection = ModelConnection(model)
        self.history: list[dict] = []
        self.last_record = None

    def clear_context(self):
        self.history.clear()
        if self.file_session:
            self.file_session.last_plan = self.file_session.last_question = None
            self.file_session.pending_request = None

    def open_file(self, path, *, format_hint=None):
        candidate = AssistantSession(path, format_hint=format_hint)
        self.file_session = candidate
        self.clear_context()

    def close_file(self):
        self.file_session = None
        self.clear_context()

    def connect(self, candidate):
        self.connection.connect(candidate)
        self.clear_context()

    def disconnect(self):
        self.connection.disconnect()
        self.clear_context()

    def ask(self, question, *, confirm=None, on_model_request=None):
        if not isinstance(question, str) or not question.strip() or len(question) > 4000:
            raise ValueError('Ask a non-blank question of at most 4000 characters.')
        help_text = local_help(question)
        if help_text is not None:
            if self.file_session:
                self.file_session.pending_request = None
            return AssistantAnswer(help_text)
        # Explicit conceptual questions use a separate, untrusted explanation channel.
        conceptual = re.match(r'^(explain\b|define\b|compare\b|what does\b|what (?:is|are) (?:a|an)\b|why\b|how (?:does|do|can|should|to)\b)', question, re.I)
        direct = _direct_plan(question)
        file_reference = re.search(r'\b(my|this|its|file|calculation|molecule|atoms)\b', question, re.I)
        if direct is not None or resolve_intent(question) is not None or (self.file_session and (file_reference or not conceptual)):
            if self.file_session is None:
                return AssistantAnswer('Open a calculation file with /open before asking for its properties.')
            if direct is None and resolve_intent(question) is None and self.connection.active is None and self.file_session.pending_request is None:
                return AssistantAnswer('Use /connect for natural-language tool selection, or use guided analysis.')
            answer = self.file_session.ask(question, self.connection.active, confirm=confirm,
                                           on_model_request=on_model_request)
            if answer.record is not None:
                self.last_record = answer.record
            return answer
        if self.file_session:
            self.file_session.pending_request = None
        if self.connection.active is None:
            return AssistantAnswer('Use /connect to choose a model for scientific conversation. '
                                   'File analysis remains available without a model.')
        if on_model_request:
            on_model_request()
        # No file state, values or scientific records enter the conceptual request.
        text = self.connection.active.explain(question, self.history)
        self.history.extend(({'role': 'user', 'content': question}, {'role': 'assistant', 'content': text}))
        self.history = self.history[-12:]
        while len(json.dumps(self.history, ensure_ascii=False).encode()) > 32768:
            self.history = self.history[2:]
        return AssistantAnswer('Model explanation · No calculation was run\n\n' + text
                               + '\n\nModel-generated explanation; not independently verified.')
