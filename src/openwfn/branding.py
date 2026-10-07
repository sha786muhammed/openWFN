"""Owner-selected pixel wordmark shared by terminal and generated web assets."""

from rich.console import Console
from rich.text import Text

WORDMARK_ROWS = (
    '▄▀▀▄ █▀▀▄ █▀▀▀ █▄  █ █   █ █▀▀▀ █▄  █',
    '█  █ █▄▄▀ █▀▀  █ ▀▄█ █ █ █ █▀▀  █ ▀▄█',
    '▀▄▄▀ █    █▄▄▄ █   █ ▀▄▀▄▀ █    █   █',
)
SUBTITLE = 'Wavefunction analysis toolkit'
_ACCENT_START = 21


def print_welcome(console: Console, *, mode: str | None = None, plain: bool = False) -> None:
    """Print only when explicitly called by an interactive welcome screen."""
    colour = not (console.no_color or plain)
    if plain or console.width < 40:
        title = Text('openWFN')
        if colour:
            title.stylize('cyan', 4)
        console.print(title)
    else:
        for row in WORDMARK_ROWS:
            title = Text(row)
            if colour:
                title.stylize('cyan', _ACCENT_START)
            console.print(title, soft_wrap=True)
    console.print(Text(SUBTITLE), overflow='fold')
    if mode:
        console.print()
        console.print(Text(mode))


def _pixels(rows, *, cell_width, half_height, left, top, accent_start=0):
    blocks = {'█': (True, True), '▀': (True, False), '▄': (False, True)}
    result = []
    for row_number, row in enumerate(rows):
        for column, character in enumerate(row):
            for half, present in enumerate(blocks.get(character, (False, False))):
                if present:
                    fill = '#43d9e8' if column >= accent_start else '#e5edf1'
                    result.append(
                        f'<rect x="{left + column * cell_width}" '
                        f'y="{top + (row_number * 2 + half) * half_height}" '
                        f'width="{cell_width}" height="{half_height}" fill="{fill}"/>')
    return '\n'.join(result)


def wordmark_svg() -> str:
    """Font-independent vector rendering of the approved terminal lettering."""
    pixels = _pixels(WORDMARK_ROWS, cell_width=12, half_height=12, left=58, top=24,
                     accent_start=_ACCENT_START)
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="560" height="120" '
            'viewBox="0 0 560 120" role="img" aria-labelledby="openwfn-title">\n'
            '<title id="openwfn-title">openWFN</title>\n'
            '<rect x="0" y="0" width="560" height="120" rx="12" fill="#11171b"/>\n'
            + pixels + '\n</svg>\n')


def icon_svg() -> str:
    """The same W glyph cropped for legibility at browser-icon size."""
    pixels = _pixels(('█   █', '█ █ █', '▀▄▀▄▀'), cell_width=4, half_height=4,
                     left=6, top=4)
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" '
            'viewBox="0 0 32 32" role="img" aria-label="openWFN">\n'
            '<title>openWFN</title>\n' + pixels + '\n</svg>\n')
