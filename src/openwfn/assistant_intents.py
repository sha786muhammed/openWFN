"""Constrained local requests; unknown language is not a guessed analysis."""

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class IntentRequest:
    family: str
    analysis: str | None
    parameters: dict = field(default_factory=dict)
    missing_slot: str | None = None


def resolve_intent(question: str) -> IntentRequest | None:
    text = ' '.join(question.casefold().split()).strip(' ?!.')
    text = re.sub(r'^please ', '', text)
    text = re.sub(r'^(?:what (?:is|are) |where (?:is |are )?(?:the )?|show (?:me )?|tell me )', '', text)
    text = re.sub(r'^(?:the |my )', '', text)
    text = re.sub(r' (?:of|for|in) (?:the |my |this )?(?:current file|file|\.?fchk|calculation)$', '', text)
    text = re.sub(r'\bhumo\b', 'homo', text)
    if text in {'homo', 'homo energy', 'homo value', 'lumo', 'lumo energy', 'lumo value',
                'homo-lumo gap', 'homo lumo gap', 'homo–lumo gap'}:
        return IntentRequest('frontier', 'frontier-all')
    if text in {'charge', 'spin', 'multiplicity', 'spin multiplicity', 'charge and spin',
                'charge and multiplicity', 'formula'}:
        return IntentRequest('summary', 'summary')
    if text in {'ir', 'ir spectra', 'ir spectrum', 'infrared spectrum'}:
        return IntentRequest('ir', 'ir-spectrum')
    if text in {'raman', 'raman spectra', 'raman spectrum'}:
        return IntentRequest('raman', 'raman-spectrum')
    if text in {'vibrations', 'vibrational spectra', 'vibrational spectrum', 'frequencies'}:
        return IntentRequest('vibrations', 'vibrations')
    if text in {'density', 'total density', 'spin density'}:
        return IntentRequest('density', None, {'kind': 'spin' if text == 'spin density' else 'total'},
                             'density-operation')
    for name, spelling in (('mulliken', 'mulliken'), ('lowdin', 'lowdin'),
                           ('lowdin', 'löwdin'), ('hirshfeld', 'hirshfeld')):
        if text in {spelling, spelling + ' charges', spelling + ' populations'}:
            return IntentRequest('population', name)
    if text in {'charges', 'atomic charges', 'population', 'populations'}:
        return IntentRequest('population', None, missing_slot='method')
    return None


def requested_family(question: str) -> IntentRequest | None:
    """Constrain model requests without interpreting arbitrary wording locally."""
    text = question.casefold()
    for family, pattern in (('ir', r'\b(?:ir|infrared)\s+(?:spectr\w*|intensit\w*)'),
                            ('raman', r'\braman\b'),
                            ('composition', r'\b(?:contribut\w*|composition)\b.*\b(?:homo|lumo|orbital)\b'),
                            ('density', r'\bdensity\b'),
                            ('frontier', r'\b(?:homo|humo|lumo)\b')):
        if re.search(pattern, text):
            return IntentRequest(family, None)
    return None
