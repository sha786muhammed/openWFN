"""Terminal interaction for the grounded scientific assistant."""

import json
import os
import sys
from pathlib import Path

from .assistant import AssistantSession
from .assistant_model import LocalModel
from .guided import build_overview
from .guided_exports import export_atomically
from .presentation import CommandContext, render


def configured_model(*, model: str | None = None, endpoint: str | None = None,
                     allow_remote: bool = False) -> LocalModel:
    return LocalModel(model or os.environ.get('OPENWFN_CHAT_MODEL', ''),
        endpoint=endpoint or os.environ.get('OPENWFN_CHAT_ENDPOINT', 'http://127.0.0.1:11434/v1'),
        allow_remote=allow_remote, api_key=os.environ.get('OPENWFN_CHAT_API_KEY'))


def run_chat(session: AssistantSession, backend: LocalModel, *, question: str | None = None,
             output_format: str = 'plain', output_path: Path | None = None,
             overwrite: bool = False, confirm_grid: bool = False) -> int:
    """Ask one question or run a terminal session; scientific output stays local."""
    from .interactive import confirm_output_path

    def confirmation(settings):
        if confirm_grid:
            return True
        if question is not None:
            return False
        print('Density settings: ' + json.dumps(settings))
        return input('Run this numerical grid? [yes/no]: ').strip().lower() == 'yes'

    def ask(text):
        return session.ask(text, backend, confirm=confirmation)

    if question is not None:
        from .app import execute
        def operation():
            answer = ask(question)
            if answer.record is None:
                raise ValueError(answer.text)
            return answer.record
        return execute(operation, CommandContext(format=output_format, output_path=output_path,
                                                overwrite=overwrite))

    print('openWFN Scientific Assistant')
    print(f'Model: {backend.model} at {backend.endpoint}')
    print('The model selects tools. openWFN supplies the values and explanations.')
    print('Commands: /inspect, /record, /save, /open, /help, /quit')
    if backend.remote:
        print('Remote access approved: questions and capability metadata go to that endpoint. '
              'Raw files, matrices and result arrays stay local.')
    last_record = None
    while True:
        try:
            text = input('You > ').strip()
            if not text:
                continue
            if text in {'/quit', '/exit'}:
                return 0
            if text == '/help':
                print('Ask about charge/spin, orbital gaps, MO composition, charges, bond orders, '
                      'density, vibrations or excited states. Missing data are never inferred. '
                      'Use /inspect for this file; /record for complete JSON; /save for confirmed '
                      'JSON export; /open to select another file; /quit to leave.')
            elif text == '/inspect':
                print(render(build_overview(session.refresh()), CommandContext(format='plain')), end='')
            elif text == '/record':
                print(json.dumps(last_record.as_dict(), indent=2) if last_record else 'No scientific result yet.')
            elif text == '/save':
                if last_record is None:
                    print('No scientific result to save.')
                    continue
                destination = confirm_output_path(session.refresh(), last_record.kind, '.json')
                if destination:
                    export_atomically(destination, lambda stage: stage.write_text(
                        json.dumps(last_record.as_dict(), indent=2, ensure_ascii=False) + '\n', encoding='utf-8'))
                    print(f'Saved: {destination.path}')
            elif text == '/open':
                selected = input('Input file (blank to cancel): ').strip()
                if selected:
                    session = AssistantSession(selected)
                    last_record = None
                    print(f'Opened: {session.source}; earlier results are no longer active.')
            elif text.startswith('/'):
                print('Unknown command. Use /help for the available commands.')
            else:
                answer = ask(text)
                last_record = answer.record
                print(answer.text)
        except EOFError:
            return 0
        except KeyboardInterrupt:
            print('\nCancelled. No partial result was saved.')
            return 0
        except (ValueError, RuntimeError, OSError) as exc:
            last_record = None
            print(f'Cannot complete this request: {exc}')


def chat_command(path: str | Path, *, model: str | None = None, endpoint: str | None = None,
                 allow_remote: bool = False, format_hint: str | None = None,
                 question: str | None = None, output_format: str = 'plain',
                 output_path: Path | None = None, overwrite: bool = False,
                 confirm_grid: bool = False) -> int:
    try:
        session = AssistantSession(path, format_hint=format_hint)
        if output_path is not None and output_path.expanduser().resolve() == session.source:
            raise ValueError('The output path cannot replace the selected input file.')
        backend = configured_model(model=model, endpoint=endpoint, allow_remote=allow_remote)
        if question is None and not (sys.stdin.isatty() and sys.stdout.isatty()):
            raise ValueError('Chat needs a terminal, or use --question for a single request.')
    except (ValueError, RuntimeError, OSError) as exc:
        print(f'{exc}\nFor chat set OPENWFN_CHAT_MODEL or --model and configure a local model server. '
              'No model is downloaded automatically. Use `openwfn FILE open` for guided analysis '
              'without a model.', file=sys.stderr)
        return 2
    return run_chat(session, backend, question=question, output_format=output_format,
                    output_path=output_path, overwrite=overwrite, confirm_grid=confirm_grid)
