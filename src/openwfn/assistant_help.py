"""Reviewed product help, separate from unverified model explanations."""


def local_help(question: str) -> str | None:
    text = ' '.join(question.casefold().split()).strip(' ?!.')
    if text in {'hi', 'hello', 'hey', 'help'}:
        return ('Hello. Use /open PATH to inspect a calculation, or /connect to choose a model '
                'for scientific conversation. Ask about HOMO/LUMO, charge, populations or spectra. '
                '/inspect shows available data; /help lists session commands.')
    if text in {'explain about the .fchk', 'explain fchk', 'what is fchk',
                'what is a fchk', 'what is an fchk', 'what is a .fchk file',
                'explain the fchk format'}:
        return ('FCHK is a formatted checkpoint: a text representation of Gaussian checkpoint data. '
                'It can contain geometry, basis information, orbitals and other calculation records; '
                'the records actually present determine available analyses.\n\n'
                'Gaussian supplies formchk for converting a binary checkpoint, for example '
                '`formchk calculation.chk calculation.fchk`. openWFN does not supply Gaussian. '
                'A formatted checkpoint alone does not establish source convergence.\n\n'
                'For your selected file use /inspect. See the format reference: '
                'https://sha786muhammed.github.io/openWFN/reference/formats-and-exports/ '
                'and Gaussian guidance: https://gaussian.com/wp-content/uploads/dl/remote.pdf')
    return None


def missing_spectrum_guidance(analysis: str) -> str:
    if analysis == 'ir-spectrum':
        return ('IR requires vibrational frequencies and IR intensities. Open a supported frequency-job '
                'output containing those records; no spectrum was calculated. '
                'Mode displacement vectors and Raman activities are separate data.')
    if analysis == 'raman-spectrum':
        return ('Raman requires vibrational frequencies and Raman activities. Open a supported frequency-job '
                'output containing those records; no spectrum was calculated. Activity is not experimental intensity.')
    if analysis == 'vibrations':
        return 'Open a supported frequency-job output containing vibrational frequencies; no modes were inferred.'
    return ''
