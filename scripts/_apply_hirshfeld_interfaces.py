"""One-shot exact-anchor patch for Task 5 Hirshfeld public interfaces.

This file is removed by the temporary branch-only workflow after a successful patch.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected exactly one anchor, found {count}: {old[:100]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# services.py: reuse the already-tested numerical kernel and expose one ResultRecord adapter.
replace_once(
    "src/openwfn/services.py",
    "from .analysis.density import density_matrix_for_kind, evaluate_density, integrate_density\n",
    "from .analysis.density import density_matrix_for_kind, evaluate_density, integrate_density\n"
    "from .analysis.hirshfeld import HirshfeldSettings, hirshfeld_population\n",
)
replace_once(
    "src/openwfn/services.py",
    "\ndef orbital_frontier(\n",
    '''\ndef hirshfeld_population_analysis(\n    data: CalculationData,\n    *,\n    settings: HirshfeldSettings | None = None,\n) -> ResultRecord:\n    """Return native neutral-pro-atom Hirshfeld populations in the common result envelope."""\n\n    result = hirshfeld_population(data, settings=settings)\n    diagnostics = result.diagnostics\n    quadrature = diagnostics.quadrature\n    warnings = list(result.warnings)\n    if data.total_density is not None:\n        warnings.extend(_density_source_warnings(data, data.total_density))\n\n    return ResultRecord(\n        kind="hirshfeld_population",\n        data={\n            "method": result.method,\n            "atoms": [\n                {\n                    "atom_index": atom.atom_index + 1,\n                    "element": atom.symbol,\n                    "effective_nuclear_charge": atom.effective_nuclear_charge,\n                    "electron_population": atom.electron_population,\n                    "charge": atom.net_charge,\n                }\n                for atom in result.atoms\n            ],\n            "diagnostics": {\n                "expected_electrons": diagnostics.expected_electrons,\n                "integrated_electrons": diagnostics.integrated_electrons,\n                "electron_count_residual": diagnostics.electron_count_residual,\n                "population_sum": diagnostics.population_sum,\n                "population_partition_residual": diagnostics.population_partition_residual,\n                "expected_molecular_charge": diagnostics.expected_molecular_charge,\n                "integrated_charge": diagnostics.integrated_charge,\n                "charge_closure_residual": diagnostics.charge_closure_residual,\n                "negligible_promolecule_points": diagnostics.negligible_promolecule_points,\n                "unresolved_promolecule_points": diagnostics.unresolved_promolecule_points,\n                "passed": diagnostics.passed,\n            },\n            "quadrature": {\n                "radial_points": quadrature.radial_points,\n                "theta_points": quadrature.theta_points,\n                "phi_points": quadrature.phi_points,\n                "radial_extent_bohr": quadrature.radial_extent_bohr,\n                "chunk_size": quadrature.chunk_size,\n            },\n            "reference_library": {\n                "id": diagnostics.reference_library_id,\n                "sha256": diagnostics.reference_library_hash,\n            },\n            "density_source": diagnostics.density_source,\n        },\n        units={\n            "effective_nuclear_charge": "e",\n            "electron_population": "electron",\n            "charge": "e",\n            "expected_electrons": "electron",\n            "integrated_electrons": "electron",\n            "electron_count_residual": "electron",\n            "population_sum": "electron",\n            "population_partition_residual": "electron",\n            "expected_molecular_charge": "e",\n            "integrated_charge": "e",\n            "charge_closure_residual": "e",\n            "radial_extent_bohr": "bohr",\n        },\n        validation_status=result.validation_status,\n        status=result.result_status,\n        warnings=tuple(dict.fromkeys(warnings)),\n    )\n\n\ndef orbital_frontier(\n''',
)

# Registry: one shared routing authority, no separate numerical implementation.
replace_once(
    "src/openwfn/analysis/registry.py",
    "from ..services import mayer_bond_orders, molecular_summary, orbital_frontier, population_analysis\n",
    '''from ..services import (\n    hirshfeld_population_analysis,\n    mayer_bond_orders,\n    molecular_summary,\n    orbital_frontier,\n    population_analysis,\n)\n''',
)
replace_once(
    "src/openwfn/analysis/registry.py",
    '''    "lowdin": AnalysisDefinition(\n''',
    '''    "hirshfeld": AnalysisDefinition(\n        "hirshfeld",\n        "1",\n        "hirshfeld_population",\n        hirshfeld_population_analysis,\n        (_ISOLATED, _BASIS, _TOTAL_DENSITY),\n    ),\n    "lowdin": AnalysisDefinition(\n''',
)

# Python API: dedicated expert method plus discoverable population(method="hirshfeld").
replace_once(
    "src/openwfn/api.py",
    "from .analysis.registry import run_analysis, run_analysis_safe\n",
    "from .analysis.hirshfeld import HirshfeldSettings\n"
    "from .analysis.registry import run_analysis, run_analysis_safe\n",
)
replace_once(
    "src/openwfn/api.py",
    '''    def population(\n        self,\n        method: Literal["mulliken", "lowdin"] = "mulliken",\n    ) -> ResultRecord:\n        """Return Mulliken or symmetric Löwdin atomic populations."""\n\n        if method not in {"mulliken", "lowdin"}:\n            raise ValueError("population method must be 'mulliken' or 'lowdin'")\n        return run_analysis_safe(self.data, method)\n''',
    '''    def hirshfeld(\n        self,\n        *,\n        settings: HirshfeldSettings | None = None,\n    ) -> ResultRecord:\n        """Return native Hirshfeld populations with optional expert numerical settings."""\n\n        return run_analysis_safe(self.data, "hirshfeld", settings=settings)\n\n    def population(\n        self,\n        method: Literal["mulliken", "lowdin", "hirshfeld"] = "mulliken",\n    ) -> ResultRecord:\n        """Return Mulliken, symmetric Löwdin, or native Hirshfeld populations."""\n\n        if method not in {"mulliken", "lowdin", "hirshfeld"}:\n            raise ValueError("population method must be 'mulliken', 'lowdin', or 'hirshfeld'")\n        return run_analysis_safe(self.data, method)\n''',
)

# CLI: expose stable defaults and explicit expert controls only for Hirshfeld.
replace_once(
    "src/openwfn/cli.py",
    "from .analysis.orbitals import frontier_orbitals\nfrom .analysis.registry import run_analysis\n",
    "from .analysis.atom_quadrature import AtomQuadratureSettings\n"
    "from .analysis.hirshfeld import HirshfeldSettings\n"
    "from .analysis.orbitals import frontier_orbitals\n"
    "from .analysis.registry import run_analysis\n",
)
replace_once(
    "src/openwfn/cli.py",
    '''    p_population = subparsers.add_parser("population", help="Mulliken and Löwdin population analysis")\n    population_commands = p_population.add_subparsers(dest="population_method", required=True)\n    population_commands.add_parser("mulliken", help="Compute Mulliken atomic populations and charges")\n    population_commands.add_parser("lowdin", help="Compute symmetric Löwdin populations and charges")\n''',
    '''    p_population = subparsers.add_parser(\n        "population", help="Mulliken, Löwdin, and Hirshfeld population analysis"\n    )\n    population_commands = p_population.add_subparsers(dest="population_method", required=True)\n    population_commands.add_parser("mulliken", help="Compute Mulliken atomic populations and charges")\n    population_commands.add_parser("lowdin", help="Compute symmetric Löwdin populations and charges")\n    p_hirshfeld = population_commands.add_parser(\n        "hirshfeld", help="Compute native neutral-pro-atom Hirshfeld populations and charges"\n    )\n    p_hirshfeld.add_argument("--radial-points", type=int, default=96)\n    p_hirshfeld.add_argument("--theta-points", type=int, default=18)\n    p_hirshfeld.add_argument("--phi-points", type=int, default=36)\n    p_hirshfeld.add_argument("--radial-extent", type=float, default=20.0, help="Radial extent in bohr")\n    p_hirshfeld.add_argument("--chunk-size", type=int, default=65536)\n    p_hirshfeld.add_argument("--molecular-density-screen", type=float, default=1.0e-12)\n    p_hirshfeld.add_argument("--promolecule-floor", type=float, default=1.0e-14)\n    p_hirshfeld.add_argument("--partition-tolerance", type=float, default=1.0e-8)\n    p_hirshfeld.add_argument("--electron-closure-tolerance", type=float, default=5.0e-3)\n    p_hirshfeld.add_argument("--charge-closure-tolerance", type=float, default=5.0e-3)\n''',
)
replace_once(
    "src/openwfn/cli.py",
    '''    if args.command == "population":\n        return execute(\n            lambda: run_analysis(\n                require_calculation(), args.population_method\n            ),\n            _context(args),\n        )\n''',
    '''    if args.command == "population":\n        if args.population_method == "hirshfeld":\n            settings = HirshfeldSettings(\n                quadrature=AtomQuadratureSettings(\n                    radial_points=args.radial_points,\n                    theta_points=args.theta_points,\n                    phi_points=args.phi_points,\n                    radial_extent_bohr=args.radial_extent,\n                    chunk_size=args.chunk_size,\n                ),\n                molecular_density_screen=args.molecular_density_screen,\n                promolecule_floor=args.promolecule_floor,\n                population_partition_tolerance=args.partition_tolerance,\n                electron_closure_tolerance=args.electron_closure_tolerance,\n                charge_closure_tolerance=args.charge_closure_tolerance,\n            )\n            return execute(\n                lambda: run_analysis(require_calculation(), "hirshfeld", settings=settings),\n                _context(args),\n            )\n        return execute(\n            lambda: run_analysis(require_calculation(), args.population_method),\n            _context(args),\n        )\n''',
)

# Guided interface: make the same default Hirshfeld analysis reachable without a second code path.
replace_once(
    "src/openwfn/interactive.py",
    '''        operation = ask("Density workflow [integrate/esp; default integrate]: ", "integrate").casefold()\n''',
    '''        operation = ask(\n            "Density/population workflow [integrate/esp/hirshfeld; default integrate]: ",\n            "integrate",\n        ).casefold()\n''',
)
replace_once(
    "src/openwfn/interactive.py",
    '''        elif operation == "esp":\n            point = tuple(float(value) for value in ask("ESP coordinates x y z in angstrom [5 0 0]: ", "5 0 0").split())\n            component = ask("ESP component [total/electronic/nuclear/mulliken/lowdin; default total]: ", "total")\n            show_result(client.esp(point, component=component))\n        else:\n            utils.print_error("Unknown density workflow.")\n''',
    '''        elif operation == "esp":\n            point = tuple(float(value) for value in ask("ESP coordinates x y z in angstrom [5 0 0]: ", "5 0 0").split())\n            component = ask("ESP component [total/electronic/nuclear/mulliken/lowdin; default total]: ", "total")\n            show_result(client.esp(point, component=component))\n        elif operation == "hirshfeld":\n            show_result(client.hirshfeld())\n        else:\n            utils.print_error("Unknown density/population workflow.")\n''',
)

# Existing deterministic registry contract must acknowledge the new first-class analysis.
replace_once(
    "tests/unit/test_analysis_registry.py",
    '''        "frontier-all",\n        "lowdin",\n''',
    '''        "frontier-all",\n        "hirshfeld",\n        "lowdin",\n''',
)

print("Hirshfeld Task 5 interface patch applied successfully")
