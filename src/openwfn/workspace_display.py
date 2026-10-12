"""Responsive, read-only presentation of a guided scientific workspace."""

from rich.console import Console, Group
from rich.table import Table
from rich.text import Text

from .guided import GuidedSession

_CATEGORIES = (
    ('Overview', 'summary'), ('Geometry', 'geometry'), ('Orbitals', 'orbitals'),
    ('Atomic charges', 'population'), ('Bond orders', 'bonds'),
    ('Density', 'density'), ('Spectra', 'vibrations'),
)
_REQUIREMENTS = {
    'summary': 'summary', 'orbitals': 'frontier-all', 'population': 'mulliken',
    'bonds': 'mayer', 'vibrations': 'vibrations',
}


def print_workspace(console: Console, session: GuidedSession, *, selected: str,
                    title: str, description: str, stage: str = 'Configure',
                    settings: tuple[tuple[str, str], ...] = ()) -> None:
    """Show file-aware navigation; never execute an analysis or create output files."""
    source = Text(session.source.name, style='bold')
    structure = session.data.structure
    if structure is not None:
        source.append(f' · {len(structure.atomic_numbers)} centers · charge '
                      f'{structure.charge if structure.charge is not None else "unknown"} · multiplicity '
                      f'{structure.multiplicity if structure.multiplicity is not None else "unknown"}')
    console.print(source, overflow='fold')
    console.print()
    steps = Text()
    for index, step in enumerate(('Choose', 'Configure', 'Run', 'Review', 'Save')):
        if index:
            steps.append(' → ', style='dim')
        steps.append(step, style='bold cyan' if step == stage else 'dim')
    console.print(steps)
    console.print()
    navigation = Text('Analyses in this file\n\n', style='bold')
    for label, command in _CATEGORIES:
        if command == 'density':
            available = session.data.basis is not None and session.data.total_density is not None
        elif command == 'geometry':
            available = structure is not None and session.data.periodic is None
        else:
            available = session.eligible(_REQUIREMENTS.get(command, command))
            if command == 'population':
                available = available or session.eligible('hirshfeld')
        navigation.append(('→ ' if selected == command else '  ') + label,
                          style='bold cyan' if selected == command else None)
        if not available:
            navigation.append(' — missing records', style='dim')
        navigation.append('\n')
    fields = Table.grid(padding=(0, 2), expand=False)
    for label, value in settings:
        fields.add_row(Text(label), Text(str(value), style='cyan', overflow='fold'))
    content = Group(Text(title, style='bold cyan'), Text(description), Text(''), fields,
                    Text(''), Text('Save folder'), Text(str(session.directory / 'results'), style='cyan',
                                                      overflow='fold'))
    if console.width >= 100:
        columns = Table.grid(padding=(0, 3), expand=True)
        columns.add_column(width=29)
        columns.add_column(ratio=1)
        columns.add_row(navigation, content)
        console.print(columns)
    else:
        # Stacking prevents a two-column layout from truncating paths or settings.
        console.print(content)
        console.print()
        missing = [label for label, command in _CATEGORIES
                   if command == 'vibrations' and not session.eligible('vibrations')]
        if missing:
            console.print(Text('Spectra — missing records', style='dim'))
    console.print()
    console.print(Text('Enter select · Esc back · Ctrl+C cancel', style='dim'))
    console.print()
