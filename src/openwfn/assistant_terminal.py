"""Terminal conversation with explicit session-only model connection controls."""

import getpass
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

from rich.console import Console

from .assistant import AssistantSession
from .assistant_connections import discover_models
from .assistant_conversation import ConversationSession
from .assistant_display import render_chat_answer, safe_terminal_text
from .assistant_model import LocalModel
from .branding import print_welcome
from .guided import build_overview
from .guided_exports import ExportLocation, export_atomically
from .presentation import CommandContext, render
from .terminal_ui import COMMANDS, ChatInput


def configured_model(*, model=None, endpoint=None, allow_remote=False):
    name = model or os.environ.get('OPENWFN_CHAT_MODEL', '')
    return LocalModel(name, endpoint=endpoint or os.environ.get('OPENWFN_CHAT_ENDPOINT',
        'http://127.0.0.1:11434/v1'), allow_remote=allow_remote,
        api_key=os.environ.get('OPENWFN_CHAT_API_KEY')) if name else None


def _choose(message, choices):
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        for index, choice in enumerate(choices, 1):
            print(f'{index}. {safe_terminal_text(choice)}')
        value = input(message + ' (number; blank cancels): ').strip()
        return choices[int(value) - 1] if value.isdigit() and 1 <= int(value) <= len(choices) else None
    import questionary
    from questionary.constants import DEFAULT_STYLE

    from .utils import color_enabled
    style = None if color_enabled() else questionary.Style([
        (selector, '') for selector, _ in DEFAULT_STYLE.style_rules])
    prompt = questionary.select(message, choices=choices, use_search_filter=True,
        use_jk_keys=False, style=style, instruction='Type to filter · arrows select · Enter choose · Esc back')
    @prompt.application.key_bindings.add('escape')
    def cancel(event):
        event.app.exit(result=None)
    return prompt.unsafe_ask()


def _connect(controller, *, same_endpoint=False):
    active = controller.connection.active
    if same_endpoint and active:
        endpoint, remote, key, transport = active.endpoint, active.remote, active.api_key, active.transport
    else:
        choice = _choose('Connect a model', ['Ollama · local', 'LM Studio · local', 'Custom endpoint', 'Cancel'])
        if not choice or choice == 'Cancel':
            return
        key, remote, transport = None, False, None
        if choice.startswith('Ollama'):
            endpoint = 'http://127.0.0.1:11434/v1'
            print('Ollama download: https://ollama.com/download · local use has no API charge.')
        elif choice.startswith('LM Studio'):
            endpoint = 'http://127.0.0.1:1234/v1'
            print('LM Studio download: https://lmstudio.ai/download · start its local server.')
        else:
            endpoint = input('Model base URL (blank cancels): ').strip()
            if not endpoint:
                return
            remote = urlsplit(endpoint).hostname not in {'localhost', '127.0.0.1', '::1'}
            if remote:
                print('Remote service: provider charges may apply. Questions and capability metadata '
                      'will go to this endpoint. Raw files and scientific result arrays stay local. '
                      'Existing conversation is not transferred.')
                if input('Approve this connection for this session? [yes/no]: ').strip().lower() != 'yes':
                    return
            key = getpass.getpass('API key (optional; session only): ') or None
    probe = LocalModel('discovery', endpoint=endpoint, allow_remote=remote, api_key=key,
                       timeout=5, transport=transport)
    while True:
        try:
            names = discover_models(probe)
            if names:
                selected = _choose('Choose a model', names)
                if selected:
                    candidate = LocalModel(selected, endpoint=endpoint, allow_remote=remote,
                                           api_key=key, transport=transport)
                    controller.connect(candidate)
                    print(f'Connected: {safe_terminal_text(selected)}. Conversation context cleared.')
                return
            print('No models available. Download a model in your runner, then check again. '
                  'Size, hardware needs and licence depend on your selection.')
        except (ValueError, RuntimeError) as exc:
            print(safe_terminal_text(str(exc)))
            print('Install/start the runner and enable its compatible server. No download was started.')
        if _choose('Next step', ['Check again', 'Return to chat']) != 'Check again':
            return


def run_chat(session: AssistantSession | None, backend: LocalModel | None, *, question=None,
             output_format='plain', output_path=None, overwrite=False, confirm_grid=False,
             context=None) -> int:
    from .interactive import confirm_output_path
    controller = ConversationSession(session, backend)
    context = context or CommandContext(input_path=session.source if session else None,
        format=output_format, output_path=output_path, overwrite=overwrite)

    def confirmation(settings):
        if confirm_grid:
            return True
        if question is not None:
            return False
        print('Density settings: ' + json.dumps(settings))
        return input('Run this numerical grid? [yes/no]: ').strip().lower() == 'yes'

    def progress():
        active = controller.connection.active
        if active and not context.quiet:
            print(f'Waiting for {safe_terminal_text(active.model)} (timeout {active.timeout:g}s). '
                  'Ctrl+C cancels; no result has been saved.', file=context.error_stream, flush=True)

    def ask(text):
        return controller.ask(text, confirm=confirmation, on_model_request=progress)

    if question is not None:
        from .app import execute
        if session is None:
            if context.format in {'json', 'csv'} or context.output_path or context.quiet:
                return execute(lambda: (_ for _ in ()).throw(ValueError(
                    'General conversation is prose, not a scientific ResultRecord. Use plain output without an output file.')), context)
            try:
                print(safe_terminal_text(ask(question).text), file=context.output_stream)
                return 0 if controller.connection.active else 2
            except (ValueError, RuntimeError, OSError) as exc:
                print(safe_terminal_text(str(exc)), file=context.error_stream)
                return 2
        def operation():
            answer = ask(question)
            if answer.record is None:
                raise ValueError(answer.text)
            return answer.record
        return execute(operation, context)

    print_welcome(Console(no_color=True if not context.color else None),
                  mode='Scientific Assistant', plain=context.format == 'plain')
    print(f'Model: {safe_terminal_text(backend.model)} · {"Remote" if backend.remote else "Local endpoint"}'
          if backend else 'No model connected · /connect for scientific conversation')
    print(f'File: {safe_terminal_text(str(session.source)) if session else "No file open"}')
    print('Ask about your file or quantum chemistry. /help shows commands.')
    if backend and backend.remote:
        print('Remote access approved: questions and capability metadata go to that endpoint. '
              'Raw files and scientific result arrays stay local.')
    prompt = ChatInput()
    while True:
        try:
            text = prompt.prompt().strip()
            if not text:
                continue
            command, _, argument = text.partition(' ')
            if command in {'/quit', '/exit'}:
                return 0
            if command == '/help':
                print('Commands: ' + ', '.join(COMMANDS))
                print('File questions use openWFN results. General explanations use your model and '
                      'are not independently verified. /record preserves complete evidence. '
                      'Ctrl+C cancels; Ctrl+D exits. Connections and history are session-only.')
            elif command in {'/connect', '/models'}:
                _connect(controller, same_endpoint=command == '/models')
            elif command == '/disconnect':
                controller.disconnect()
                print('Disconnected. File and scientific records retained; runner was not stopped.')
            elif command == '/clear':
                controller.clear_context()
                print('Conversation context cleared. File, connection and scientific records retained.')
            elif command == '/close':
                controller.close_file()
                print('File closed. General conversation remains available; earlier records retain their source.')
            elif command == '/inspect':
                print(render(build_overview(controller.file_session.refresh()), CommandContext(format='plain'))
                      if controller.file_session else 'No file open. Use /open PATH.')
            elif command == '/record':
                print(json.dumps(controller.last_record.as_dict(), indent=2) if controller.last_record else 'No scientific result yet.')
            elif command == '/save':
                record = controller.last_record
                if record is None:
                    print('No scientific result to save. Model explanations are not scientific records.')
                    continue
                source = record.provenance.get('source_path')
                if not source:
                    raise ValueError('Record source unavailable; cannot safely select an export destination.')
                destination = confirm_output_path(ExportLocation(Path(source), Path.cwd()), record.kind, '.json')
                if destination:
                    export_atomically(destination, lambda stage: stage.write_text(
                        json.dumps(record.as_dict(), indent=2, ensure_ascii=False) + '\n', encoding='utf-8'))
                    print(f'Saved: {destination.path}')
            elif command == '/open':
                selected = argument.strip() or input('Input file (blank cancels): ').strip()
                if selected:
                    controller.open_file(selected)
                    print(f'Opened: {safe_terminal_text(str(controller.file_session.source))}; file context reset.')
            elif command.startswith('/'):
                print('Unknown command. Use /help.')
            else:
                answer = ask(text)
                print(render_chat_answer(answer, question=text, source_label=(
                    controller.file_session.source.name if controller.file_session else None)))
        except EOFError:
            return 0
        except KeyboardInterrupt:
            if controller.file_session:
                controller.file_session.pending_request = None
            print('\nCancelled. No partial result was saved. /quit exits.')
        except (ValueError, RuntimeError, OSError) as exc:
            print('Cannot complete this request: ' + safe_terminal_text(str(exc)))


def chat_command(path=None, *, model=None, endpoint=None, allow_remote=False, format_hint=None,
                 question=None, output_format='plain', output_path=None, overwrite=False,
                 confirm_grid=False, context=None, non_interactive=False) -> int:
    context = context or CommandContext(input_path=Path(path) if path else None,
        format=output_format, output_path=output_path, overwrite=overwrite)
    try:
        if question is None and (non_interactive or context.quiet or context.format in {'json', 'csv'}
                                 or context.output_path is not None):
            raise ValueError('Use --question for structured, quiet, output-file or non-interactive chat.')
        session = AssistantSession(path, format_hint=format_hint) if path else None
        if session and output_path is not None and output_path.expanduser().resolve() == session.source:
            raise ValueError('The output path cannot replace the selected input file.')
        backend = configured_model(model=model, endpoint=endpoint, allow_remote=allow_remote)
        if question is None and not (sys.stdin.isatty() and sys.stdout.isatty()):
            raise ValueError('Chat needs a terminal, or use --question for a single request.')
    except (ValueError, RuntimeError, OSError) as exc:
        if context.format == 'json':
            from .app import _report_failure
            _report_failure(exc, context)
        else:
            print(safe_terminal_text(str(exc)), file=context.error_stream)
        return 2
    from .utils import terminal_color
    with terminal_color(context.color and context.format != 'plain'):
        return run_chat(session, backend, question=question, output_format=output_format,
            output_path=output_path, overwrite=overwrite, confirm_grid=confirm_grid, context=context)
