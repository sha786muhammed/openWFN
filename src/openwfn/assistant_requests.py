"""Typed, file-bound clarification state, independent of model memory."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .assistant_intents import IntentRequest

if TYPE_CHECKING:
    from .assistant import AnalysisPlan


@dataclass(frozen=True)
class PendingRequest:
    original_question: str
    intent: IntentRequest | None
    clarification: str
    resolved_slots: dict
    source_sha256: str
    attempts: int = 0


def bind_reply(pending: PendingRequest, reply: str) -> 'PendingRequest | AnalysisPlan | None':
    from .assistant import AnalysisPlan

    text = reply.casefold().strip(' ?!.')
    for prefix in ('use ', 'please use '):
        if text.startswith(prefix):
            text = text[len(prefix):]
    text = text.replace('löwdin', 'lowdin')
    choices = {'method': ('mulliken', 'lowdin', 'hirshfeld'),
               'projection-method': ('mulliken', 'lowdin'), 'spin': ('alpha', 'beta', 'all'),
               'orbital': ('homo', 'lumo'), 'density-operation': ('integrate', 'integration', 'cube', 'point')}
    slot = pending.clarification
    if slot in choices:
        if text not in choices[slot] and not (slot == 'orbital' and text.isdecimal() and int(text) > 0):
            return None
        value = int(text) if slot == 'orbital' and text.isdecimal() else text
    elif slot == 'state':
        text = text.removeprefix('state ').removeprefix('mode ')
        if not text.isdecimal() or not 1 <= int(text) <= 4096:
            return None
        value = int(text)
    elif slot == 'points':
        try:
            from math import isfinite
            numbers = [float(x) for x in text.replace(',', ' ').split()]
            if len(numbers) != 3 or not all(isfinite(x) and abs(x) <= 1e9 for x in numbers):
                return None
        except ValueError:
            return None
        value = dict(zip(('x_bohr', 'y_bohr', 'z_bohr'), numbers))
    else:
        return None
    slots = {**pending.resolved_slots, slot: value}
    if pending.intent and pending.intent.family == 'population' and slot == 'method':
        return AnalysisPlan('analysis', value)
    if pending.intent and pending.intent.family == 'density' and slot == 'density-operation':
        if value in {'integrate', 'integration'}:
            return AnalysisPlan('analysis', 'density', pending.intent.parameters)
        # Cube/point require workflows not supplied by this read-only request.
        return replace(pending, resolved_slots=slots)
    return replace(pending, resolved_slots=slots)
