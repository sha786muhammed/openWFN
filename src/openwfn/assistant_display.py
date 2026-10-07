"""Compact terminal answers derived only from existing scientific records."""

import re

from .assistant import AssistantAnswer
from .presentation import CommandContext, render


def safe_terminal_text(text: str) -> str:
    """Keep prose, tabs and newlines; never execute model/server escape sequences."""
    return ''.join(char for char in text if char in '\n\t' or 32 <= ord(char) < 127 or ord(char) >= 160)


def render_chat_answer(answer: AssistantAnswer, *, question: str, source_label: str | None) -> str:
    if answer.record is None:
        return safe_terminal_text(answer.text)
    record = answer.record
    data = record.data
    lines = []
    text = question.casefold().replace('humo', 'homo')
    requested = re.search(r'\b(homo|lumo)\b', text)
    if record.status != 'failed' and 'gap' in text and record.kind == 'frontier_orbitals':
        channels = [(data.get('spin', 'orbital'), data)] if 'gap_ev' in data else [
            (name, data.get(name)) for name in ('alpha', 'beta')]
        for name, channel in channels:
            if isinstance(channel, dict) and channel.get('gap_ev') is not None:
                lines.append(f'HOMO–LUMO gap ({channel.get("spin", name)}): {channel["gap_ev"]} eV.')
        if lines:
            lines.append('An orbital energy gap is not an optical excitation energy.')
    elif record.status != 'failed' and requested and record.kind == 'frontier_orbitals':
        orbital = requested[1]
        if orbital == 'homo' and data.get('overall_homo_hartree') is not None:
            lines.append(f'HOMO: orbital {data["overall_homo_number"]}, {data["overall_homo_hartree"]} Hartree.')
        else:
            channels = [(data.get('spin', 'orbital'), data)] if 'homo_hartree' in data else [
                (name, data.get(name)) for name in ('alpha', 'beta')]
            for name, channel in channels:
                if isinstance(channel, dict) and channel.get(orbital + '_hartree') is not None:
                    lines.append(f'{orbital.upper()} ({channel.get("spin", name)}): orbital '
                                 f'{channel.get(orbital + "_number")}, {channel[orbital + "_hartree"]} Hartree.')
        if data.get('reference_kind') == 'restricted_closed_shell':
            lines.append('Restricted closed-shell calculation.')
    if not lines:
        lines.append(render(record, CommandContext(format='plain')).strip())
    else:
        lines.append(f'Result: {record.status} · Analysis status: {record.validation_status}')
        lines.extend('Warning: ' + warning for warning in record.warnings)
    source = source_label or record.provenance.get('source_path', 'source unavailable')
    lines.append(f'Source: {source}\n/record for the complete result, units and provenance.')
    return safe_terminal_text('\n\n'.join(lines))
