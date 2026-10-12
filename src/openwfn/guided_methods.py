"""Explicit settings and review for registered scientific analyses."""

from collections.abc import Callable
from dataclasses import asdict, is_dataclass

import numpy as np

from .analysis.registry import run_analysis_safe
from .guided import GuidedSession
from .palette import Workflow
from .results import ResultRecord


def method_groups(session: GuidedSession) -> tuple[tuple[str, tuple[Workflow, ...]], ...]:
    """Group registered methods and show per-file requirements, without running them."""
    from .analysis.registry import available_analyses

    families = (
        ('Structure and metadata', ('summary',)),
        ('Orbitals and composition', ('frontier-all', 'frontier', 'beta-frontier', 'orbital-composition')),
        ('Charges and bond orders', ('mulliken', 'lowdin', 'hirshfeld', 'mayer')),
        ('Density of states', ('dos', 'pdos')),
        ('Vibrations and spectra', ('vibrations', 'normal-mode', 'ir-spectrum', 'raman-spectrum')),
        ('Excitations and UV–Vis', ('excited-states', 'excited-state', 'transition-dipoles', 'uvvis-spectrum', 'nto')),
        ('Density fields and localization', ('density-derivatives', 'kinetic-energy-density', 'elf', 'lol', 'nci')),
        ('QTAIM topology', ('qtaim',)),
    )
    registered = set(available_analyses())
    assigned = {name for _, names in families for name in names}
    families += (('Other registered methods', tuple(sorted(registered - assigned))),)
    groups = []
    for title, names in families:
        choices = []
        for name in names:
            if name not in registered:
                continue
            label = name.replace('-', ' ')
            if not session.eligible(name):
                reasons = session.analyses.get(name, {}).get('missing_requirements', ())
                label += ' — unavailable: ' + ', '.join(reasons)
            choices.append(Workflow(label, name))
        if choices:
            groups.append((title, tuple(choices)))
    return tuple(groups)


def run_guided_method(session: GuidedSession, name: str, *,
                      ask: Callable[[str], str] = input) -> ResultRecord | None:
    """Configure an existing method; absent records never trigger calculation."""
    if not session.eligible(name):
        return run_analysis_safe(session.data, name)
    parameters = {}

    def value(label: str, default: str) -> str:
        return ask(f'{label} [{default}]: ').strip() or default

    def curve_range(lower_key: str, upper_key: str, unit: str) -> None:
        lower = value(f'Curve minimum in {unit} (auto for source range)', 'auto')
        upper = value(f'Curve maximum in {unit} (auto for source range)', 'auto')
        if lower != 'auto' or upper != 'auto':
            if lower == 'auto' or upper == 'auto':
                raise ValueError('Provide both curve limits, or choose auto for both.')
            parameters.update({lower_key: float(lower), upper_key: float(upper)})
        points = value('Curve points (auto or positive integer)', 'auto')
        if points != 'auto':
            parameters['points'] = int(points)

    try:
        if name == 'mayer':
            parameters['threshold'] = float(value('Display threshold', '0.05'))
        elif name == 'orbital-composition':
            mo = value('Orbital (homo/lumo/one-based number)', 'homo')
            parameters.update(mo=int(mo) if mo.isdigit() else mo,
                              spin=value('Spin channel (alpha/beta)', 'alpha'),
                              method=value('Method (lowdin/mulliken)', 'lowdin'))
        elif name in {'dos', 'pdos'}:
            parameters.update(spin=value('Spin channel (all/alpha/beta)', 'all'),
                              sigma_ev=float(value('Gaussian sigma in eV', '0.3')))
            lower = value('Energy minimum in eV (auto for full orbital range)', 'auto')
            upper = value('Energy maximum in eV (auto for full orbital range)', 'auto')
            if lower != 'auto' or upper != 'auto':
                if lower == 'auto' or upper == 'auto':
                    raise ValueError('Provide both energy limits, or choose auto for both.')
                parameters.update(energy_min_ev=float(lower), energy_max_ev=float(upper))
            points = value('Energy grid points (auto or positive integer)', 'auto')
            if points != 'auto':
                parameters['points'] = int(points)
            if name == 'pdos':
                parameters.update(method=value('Method (lowdin/mulliken)', 'lowdin'),
                                  group_by=value('Group by (atom/element/angular)', 'atom'))
        elif name in {'normal-mode', 'excited-state', 'nto'}:
            label = 'mode' if name == 'normal-mode' else 'state'
            parameters[label] = int(value(f'One-based {label} number', '1'))
        elif name in {'ir-spectrum', 'raman-spectrum'}:
            parameters['fwhm_cm1'] = float(value('Broadening FWHM in cm^-1', '20'))
            curve_range('frequency_min_cm1', 'frequency_max_cm1', 'cm^-1')
        elif name == 'uvvis-spectrum':
            parameters['fwhm_ev'] = float(value('Broadening FWHM in eV', '0.20'))
            curve_range('energy_min_ev', 'energy_max_ev', 'eV')
        elif name == 'hirshfeld':
            from .analysis.atom_quadrature import AtomQuadratureSettings
            from .analysis.hirshfeld import HirshfeldSettings

            parameters['settings'] = HirshfeldSettings(quadrature=AtomQuadratureSettings(
                radial_points=int(value('Radial quadrature points', '96')),
                theta_points=int(value('Polar angular points', '18')),
                phi_points=int(value('Azimuthal angular points', '36')),
                radial_extent_bohr=float(value('Radial extent in bohr', '20'))))
        elif name == 'qtaim':
            from .analysis.qtaim import QTAIMSettings

            seeds = value('Seeds x y z in bohr, separated by semicolons (auto for engine seeds)', 'auto')
            if seeds != 'auto':
                rows = [[float(item) for item in row.split()] for row in seeds.split(';')]
                if not rows or any(len(row) != 3 for row in rows):
                    raise ValueError('Each seed must contain exactly three coordinates in bohr.')
                parameters['seeds_bohr'] = np.asarray(rows)
            parameters['settings'] = QTAIMSettings(max_iterations=int(value('Maximum search iterations per seed', '64')))
            paths = value('Include bounded bond paths (yes/no)', 'no').casefold()
            if paths not in {'yes', 'no'}:
                raise ValueError('Choose yes or no for bounded bond paths.')
            parameters['include_bond_paths'] = paths == 'yes'
        elif name in {'density-derivatives', 'kinetic-energy-density', 'elf', 'lol', 'nci'}:
            point = [float(component) for component in value('Point x y z in bohr', '0.31 0.47 0.83').split()]
            if len(point) != 3:
                raise ValueError('Provide exactly three coordinates in bohr.')
            parameters['points_bohr'] = np.array([point])
            if name in {'elf', 'lol'}:
                parameters['channel'] = value('Channel (total only for closed-shell; alpha/beta)', 'alpha')
            elif name == 'density-derivatives':
                parameters['kind'] = value('Density component (total/alpha/beta/spin)', 'total')
            elif name == 'kinetic-energy-density':
                parameters['kind'] = value('Density component (total/alpha/beta)', 'total')
        if name in {'excited-state', 'excited-states', 'transition-dipoles', 'uvvis-spectrum', 'nto'}:
            from .excited_states import get_excited_state_collection
            collection = get_excited_state_collection(session.data.calculation)
            if collection is not None and len(collection.jobs) > 1:
                print('Source jobs: ' + ', '.join(f'{job.index}: {job.method_detail}' for job in collection.jobs))
                parameters['job'] = int(value('Source job number', '1'))
        print(f'\nReview calculation: {name}')
        for key, item in parameters.items():
            shown = item.tolist() if isinstance(item, np.ndarray) else asdict(item) if is_dataclass(item) else item
            print(f'{key.replace("_", " ")}: {shown}')
        if name == 'qtaim':
            print('Bounded critical-point search; not exhaustive topology or basin integration.')
        if name == 'hirshfeld':
            print('Uses the installed atomic reference library; check quadrature convergence before using charges.')
        if value('Run calculation or return (run/back)', 'run').casefold() != 'run':
            return None
        return run_analysis_safe(session.data, name, **parameters)
    except ValueError as exc:
        return ResultRecord.failure(kind='guided_settings', analysis_name=name,
                                    analysis_version='1', exception=exc, elapsed_seconds=0)
