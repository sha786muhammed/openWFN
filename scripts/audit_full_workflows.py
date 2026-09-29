#!/usr/bin/env python3
"""Throwaway post-release audit harness for openWFN 0.8.1.

This script intentionally lives only on the audit branch. It exercises the
public CLI and Python API against repository and pinned external fixtures and
writes a machine-readable report. It is not product code.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Entry:
    name: str
    surface: str
    status: str
    detail: str = ""
    returncode: int | None = None
    stdout_tail: str = ""
    stderr_tail: str = ""


def tail(text: str, limit: int = 1200) -> str:
    text = text.strip()
    return text[-limit:] if len(text) > limit else text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    entries: list[Entry] = []
    workspace = Path(tempfile.mkdtemp(prefix="openwfn-audit-"))

    water = ROOT / "examples/water/water.fchk"
    methane = ROOT / "examples/methane/methane.fchk"
    ammonia = ROOT / "examples/ammonia/ammonia.fchk"
    ecp = ROOT / "tests/fixtures/scientific/ecp_minimal.fchk"
    ghost = ROOT / "tests/fixtures/scientific/ghost_minimal.fchk"
    uhf = ROOT / "tests/fixtures/scientific/uhf_beta_homo.fchk"
    rohf = ROOT / "tests/fixtures/scientific/rohf_open_shell.fchk"
    post_hf = ROOT / "tests/fixtures/scientific/post_hf_scf_density.fchk"

    ext = {
        "benzene": args.input_root / "QuickFF/quickff/data/systems/benzene/gaussian.fchk",
        "lih": args.input_root / "iodata/iodata/test/data/li_h_3-21G_hf_g09.fchk",
        "o2_pure": args.input_root / "iodata/iodata/test/data/o2_cc_pvtz_pure.fchk",
        "o2_cart": args.input_root / "iodata/iodata/test/data/o2_cc_pvtz_cart.fchk",
        "acetylene": args.input_root / "iodata/iodata/test/data/psi4_hcch.fchk",
        "helium_high_l": args.input_root / "iodata/iodata/test/data/he_spdfgh_orbital.fchk",
    }

    for label, path in {
        "water": water,
        "methane": methane,
        "ammonia": ammonia,
        "ecp": ecp,
        "ghost": ghost,
        "uhf": uhf,
        "rohf": rohf,
        "post_hf": post_hf,
        **ext,
    }.items():
        if not path.is_file():
            entries.append(Entry(f"fixture:{label}", "fixture", "failed", f"missing {path}"))

    def cli(
        name: str,
        argv: list[str],
        *,
        expected_codes: set[int] | None = None,
        stdin: str | None = None,
        outputs: tuple[Path, ...] = (),
        timeout: int = 120,
    ) -> None:
        expected = expected_codes or {0}
        env = dict(os.environ)
        env.setdefault("MPLBACKEND", "Agg")
        try:
            proc = subprocess.run(
                ["openwfn", *argv],
                input=stdin,
                text=True,
                capture_output=True,
                timeout=timeout,
                cwd=workspace,
                env=env,
                check=False,
            )
        except Exception as exc:
            entries.append(Entry(name, "cli", "failed", repr(exc)))
            return
        missing = [str(path) for path in outputs if not path.exists() or path.stat().st_size == 0]
        ok = proc.returncode in expected and not missing
        detail = ""
        if missing:
            detail = "missing/empty outputs: " + ", ".join(missing)
        entries.append(
            Entry(
                name,
                "cli",
                "passed" if ok else "failed",
                detail,
                proc.returncode,
                tail(proc.stdout),
                tail(proc.stderr),
            )
        )

    # Packaging / command startup / implicit command routing.
    cli("version", ["--version"])
    cli("implicit-summary-nontty", [str(water)])
    cli("examples-install", ["examples", "install", str(workspace / "installed-examples")], outputs=(workspace / "installed-examples/water.fchk",))

    # Legacy and modern geometry / structure surfaces.
    cli("summary-water", [str(water), "summary"])
    cli("info-water", [str(water), "info"])
    cli("doctor-water", [str(water), "doctor"])
    cli("legacy-dist", [str(water), "dist", "1", "2"])
    cli("legacy-angle", [str(water), "angle", "2", "1", "3"])
    cli("legacy-dihedral", [str(methane), "dihedral", "2", "1", "3", "4"])
    cli("geometry-distance", [str(water), "geometry", "distance", "1", "2"])
    cli("geometry-angle", [str(water), "geometry", "angle", "2", "1", "3"])
    cli("geometry-dihedral", [str(methane), "geometry", "dihedral", "2", "1", "3", "4"])
    cli("bonds", [str(water), "bonds"])
    cli("graph", [str(water), "graph"])
    xyz_legacy = workspace / "legacy.xyz"
    cli("xyz", [str(water), "xyz", str(xyz_legacy)], outputs=(xyz_legacy,))
    viewer = workspace / "viewer.html"
    cli("view", [str(water), "view", "--save", str(viewer), "--no-open"], outputs=(viewer,))
    cli("interactive-quit", [str(water), "interactive"], stdin="q\n", timeout=30)

    # Population / orbital surfaces.
    cli("population-mulliken", [str(water), "population", "mulliken"])
    cli("population-lowdin", [str(water), "population", "lowdin"])
    cli("frontier-alpha", [str(water), "orbitals", "frontier", "--spin", "alpha"])
    cli("frontier-uhf-alpha", [str(ext["o2_pure"]), "orbitals", "frontier", "--spin", "alpha"])
    cli("frontier-uhf-beta", [str(ext["o2_pure"]), "orbitals", "frontier", "--spin", "beta"])
    cli("frontier-uhf-all", [str(ext["o2_pure"]), "orbitals", "frontier", "--spin", "all"])
    cli("frontier-synthetic-uhf-all", [str(uhf), "orbitals", "frontier", "--spin", "all"])
    cli("frontier-synthetic-rohf-all", [str(rohf), "orbitals", "frontier", "--spin", "all"])

    # Density and cube paths, including zero-spin singlet validation.
    cli("density-total", [str(water), "density", "integrate", "--kind", "total", "--spacing", "0.15", "--padding", "6"])
    cli("density-alpha", [str(water), "density", "integrate", "--kind", "alpha", "--spacing", "0.20", "--padding", "6"])
    cli("density-beta", [str(water), "density", "integrate", "--kind", "beta", "--spacing", "0.20", "--padding", "6"])
    cli("density-spin-zero", [str(water), "density", "integrate", "--kind", "spin", "--spacing", "0.20", "--padding", "6"])
    cube_total = workspace / "density-total.cube"
    cli("density-cube-total", ["--overwrite", str(water), "density", "cube", str(cube_total), "--kind", "total", "--spacing", "0.25", "--padding", "5"], outputs=(cube_total,))
    cube_spin = workspace / "density-spin.cube"
    cli("cube-alias-spin", ["--overwrite", str(water), "cube", str(cube_spin), "--kind", "spin", "--spacing", "0.25", "--padding", "5"], outputs=(cube_spin,))
    cli("doctor-cube", [str(cube_total), "doctor"])
    cli("validate-density", [str(water), "validate", "--spacing", "0.15", "--padding", "6"])

    # ESP components.
    for component in ("nuclear", "mulliken", "lowdin", "electronic", "total"):
        cli(f"esp-{component}", [str(water), "esp", "point", "0", "0", "5", "--component", component, "--spacing", "0.25", "--padding", "5"])
    cli("esp-ecp-nuclear", [str(ecp), "esp", "point", "0", "0", "5", "--component", "nuclear"])
    cli("esp-ghost-nuclear", [str(ghost), "esp", "point", "0", "0", "5", "--component", "nuclear"])

    # Reports / workbench / exports / conversions / plots.
    report_html = workspace / "report.html"
    report_md = workspace / "report.md"
    cli("report-html", ["--overwrite", str(water), "report", "build", str(report_html), "--report-format", "html"], outputs=(report_html,))
    cli("report-markdown", ["--overwrite", str(water), "report", "build", str(report_md), "--report-format", "markdown"], outputs=(report_md,))
    workbench = workspace / "workbench.html"
    cli("workbench", ["--overwrite", str(water), "workbench", str(workbench)], outputs=(workbench,))
    for fmt in ("xyz", "pdb", "mol", "sdf"):
        out = workspace / f"converted.{fmt}"
        cli(f"convert-{fmt}", ["--overwrite", str(water), "convert", "--to", fmt, "--output", str(out)], outputs=(out,))
    for analysis in ("frontier", "mulliken", "lowdin"):
        out = workspace / f"{analysis}.csv"
        cli(f"export-{analysis}", ["--overwrite", str(water), "export", analysis, str(out)], outputs=(out,))
    frontier_png = workspace / "frontier.png"
    cli("plot-frontier", ["--overwrite", str(water), "plot", "frontier", str(frontier_png), "--dpi", "120"], outputs=(frontier_png,))

    # Batch discovery, parallel execution, resume, and spin routing.
    batch_dir = workspace / "batch"
    cli("batch-dry-run", [str(ROOT / "examples"), "batch", "--recursive", "--dry-run", "--analyses", "summary,frontier"])
    cli("batch-parallel", [str(ROOT / "examples"), "batch", "--recursive", "--analyses", "summary,frontier", "--workers", "2", "--output-dir", str(batch_dir)])
    cli("batch-resume", [str(ROOT / "examples"), "batch", "--recursive", "--analyses", "summary,frontier", "--workers", "2", "--resume", "--output-dir", str(batch_dir)])
    batch_spin = workspace / "batch-spin"
    cli("batch-spin-all", [str(ext["o2_pure"]), "batch", "--analyses", "frontier", "--spin", "all", "--output-dir", str(batch_spin)])

    # Expected graceful failures / environment-dependent paths.
    dummy_chk = workspace / "dummy.chk"
    dummy_chk.write_bytes(b"not a Gaussian checkpoint")
    cli("formchk-missing-utility", [str(dummy_chk), "formchk"], expected_codes={1})
    cli("structure-only-summary-rejected", [str(xyz_legacy), "summary"], expected_codes={1, 2})

    # Hidden experimental developer-preview path: audit it but do not treat an
    # explicit Experimental/Unsupported failure as a release-blocking contract.
    vtk = workspace / "mo.vtk"
    cli("experimental-mo-export", [str(water), "mo", "1", "--export", str(vtk)], expected_codes={0, 1, 2})

    # Special parser / dataset smoke cases.
    for label, path in ext.items():
        cli(f"external-summary:{label}", [str(path), "summary"])
        cli(f"external-frontier:{label}", [str(path), "orbitals", "frontier"])
    cli("external-population:benzene-mulliken", [str(ext["benzene"]), "population", "mulliken"])
    cli("external-population:lih-lowdin", [str(ext["lih"]), "population", "lowdin"])
    cli("external-o2-cart-all-spin", [str(ext["o2_cart"]), "orbitals", "frontier", "--spin", "all"])
    cli("summary-ecp", [str(ecp), "summary"])
    cli("summary-ghost", [str(ghost), "summary"])
    cli("summary-post-hf", [str(post_hf), "summary"])

    # Public Python API. Keep this separate from CLI routing so serialization
    # or presentation bugs cannot mask API failures.
    try:
        from openwfn import available_analyses, load, run_batch

        calc = load(water)
        api_calls: list[tuple[str, Callable[[], object]]] = [
            ("api-analyze-geometry", calc.analyze_geometry),
            ("api-summary", lambda: calc.analyze("summary")),
            ("api-frontier", lambda: calc.orbitals("alpha")),
            ("api-mulliken", lambda: calc.population("mulliken")),
            ("api-lowdin", lambda: calc.population("lowdin")),
            ("api-density-total", lambda: calc.density("total", spacing_bohr=0.20, padding_bohr=6.0)),
            ("api-density-spin-zero", lambda: calc.density("spin", spacing_bohr=0.20, padding_bohr=6.0)),
            ("api-geometry-distance", lambda: calc.geometry_distance(1, 2)),
            ("api-geometry-angle", lambda: calc.geometry_angle(2, 1, 3)),
        ]
        for name, fn in api_calls:
            try:
                result = fn()
                status = getattr(result, "status", None)
                ok = status in {"success", "partial"}
                entries.append(Entry(name, "python-api", "passed" if ok else "failed", f"status={status}"))
            except Exception as exc:
                entries.append(Entry(name, "python-api", "failed", repr(exc)))

        try:
            o2 = load(ext["o2_pure"])
            result = o2.orbitals("all")
            entries.append(Entry("api-uhf-frontier-all", "python-api", "passed" if result.status in {"success", "partial"} else "failed", f"status={result.status}; data={result.data}"))
        except Exception as exc:
            entries.append(Entry("api-uhf-frontier-all", "python-api", "failed", repr(exc)))

        try:
            manifest = run_batch(
                [water, methane, ammonia],
                None,
                2,
                workspace / "api-batch",
                analyses=("summary", "frontier"),
                frontier_spin="alpha",
            )
            bad = [record for record in manifest.records if record.status == "error"]
            entries.append(Entry("api-run-batch", "python-api", "passed" if not bad else "failed", f"records={len(manifest.records)}; errors={len(bad)}; analyses={manifest.analyses}"))
        except Exception as exc:
            entries.append(Entry("api-run-batch", "python-api", "failed", repr(exc)))

        entries.append(Entry("api-available-analyses", "python-api", "passed", ",".join(available_analyses())))
    except Exception as exc:
        entries.append(Entry("python-api-import", "python-api", "failed", repr(exc)))

    failures = [entry for entry in entries if entry.status == "failed"]
    payload = {
        "schema_version": "1.0",
        "workspace": str(workspace),
        "summary": {"total": len(entries), "passed": len(entries) - len(failures), "failed": len(failures)},
        "entries": [asdict(entry) for entry in entries],
    }
    (args.output_dir / "workflow-audit.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# openWFN full workflow audit",
        "",
        f"Total: {len(entries)}  Passed: {len(entries) - len(failures)}  Failed: {len(failures)}",
        "",
        "| Surface | Workflow | Status | Detail |",
        "|---|---|---|---|",
    ]
    for entry in entries:
        detail = entry.detail.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {entry.surface} | {entry.name} | {entry.status} | {detail} |")
    (args.output_dir / "workflow-audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
