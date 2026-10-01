from pathlib import Path

import pytest

from openwfn.data import OpenWFNData, SourceMetadata
from openwfn.errors import ParseError
from openwfn.ingest import load_input
from openwfn.model import Provenance

ROOT = Path(__file__).resolve().parents[2]
WATER_FCHK = ROOT / "examples" / "water" / "water.fchk"


def test_fchk_prefers_native_parser(monkeypatch) -> None:
    def unexpected_backend(*_args, **_kwargs):
        raise AssertionError("IOData backend must not be used for FCHK")

    monkeypatch.setattr("openwfn.ingest._load_iodata", unexpected_backend)
    data = load_input(WATER_FCHK)

    assert data.calculation is not None
    assert data.provenance is not None
    assert data.provenance.parser == "gaussian-fchk"
    assert data.provenance.source_format == "fchk"


@pytest.mark.parametrize(
    ("filename", "contents", "expected_format"),
    [
        ("water.xyz", "1\nwater\nO 0 0 0\n", "xyz"),
        (
            "water.pdb",
            "ATOM      1  O   HOH A   1       0.000   0.000   0.000  1.00  0.00           O\n",
            "pdb",
        ),
        (
            "water.sdf",
            "water\nopenWFN\n\n  1  0  0  0  0  0            999 V2000\n"
            "    0.0000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n"
            "M  END\n$$$$\n",
            "sdf",
        ),
    ],
)
def test_native_structure_formats_remain_preferred(
    monkeypatch, tmp_path: Path, filename: str, contents: str, expected_format: str
) -> None:
    def unexpected_backend(*_args, **_kwargs):
        raise AssertionError("IOData backend must not replace stronger native parser")

    monkeypatch.setattr("openwfn.ingest._load_iodata", unexpected_backend)
    source = tmp_path / filename
    source.write_text(contents, encoding="utf-8")

    data = load_input(source)

    assert data.calculation is not None
    assert data.provenance is not None
    assert data.provenance.source_format == expected_format


def test_native_cube_remains_preferred(monkeypatch, tmp_path: Path) -> None:
    def unexpected_backend(*_args, **_kwargs):
        raise AssertionError("IOData backend must not replace native cube parser")

    monkeypatch.setattr("openwfn.ingest._load_iodata", unexpected_backend)
    source = tmp_path / "density.cube"
    source.write_text(
        "density\nfixture\n0 0 0 0\n1 1 0 0\n1 0 1 0\n1 0 0 1\n0.5\n",
        encoding="utf-8",
    )

    data = load_input(source)

    assert len(data.grids) == 1
    assert data.grids[0].shape == (1, 1, 1)
    assert data.provenance is not None
    assert data.provenance.source_format == "cube"


def test_gaussian_out_with_gaussian_markers_stays_native(monkeypatch, tmp_path: Path) -> None:
    def unexpected_backend(*_args, **_kwargs):
        raise AssertionError("Gaussian output must stay on native parser")

    monkeypatch.setattr("openwfn.ingest._load_iodata", unexpected_backend)
    source = tmp_path / "job.out"
    source.write_text(
        "# RHF/3-21G\nSCF Done: E(RHF) = -7.5\nNormal termination of Gaussian\n",
        encoding="utf-8",
    )

    data = load_input(source)

    assert data.calculation is None
    assert data.metadata.source_program == "Gaussian"
    assert data.metadata.energy_hartree == pytest.approx(-7.5)
    assert data.provenance is not None
    assert data.provenance.source_format == "gaussianlog"


def test_orca_out_routes_to_iodata(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_backend(path: Path, *, format_id: str) -> OpenWFNData:
        calls.append(format_id)
        return OpenWFNData(
            calculation=None,
            structure=None,
            periodic=None,
            grids=(),
            integrals=None,
            metadata=SourceMetadata(source_program="ORCA"),
            provenance=Provenance(
                source_path=str(path),
                sha256="2" * 64,
                parser="openwfn-iodata-adapter",
                source_format=format_id,
            ),
        )

    monkeypatch.setattr("openwfn.ingest._load_iodata", fake_backend)
    source = tmp_path / "job.out"
    source.write_text(
        "                         O   R   C   A\nFINAL SINGLE POINT ENERGY     -75.0\n",
        encoding="utf-8",
    )

    data = load_input(source)

    assert calls == ["orcalog"]
    assert data.metadata.source_program == "ORCA"


def test_cp2k_named_output_routes_to_cp2klog(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_backend(_path: Path, *, format_id: str) -> OpenWFNData:
        calls.append(format_id)
        return OpenWFNData(None, None, None, (), None, SourceMetadata(), None)

    monkeypatch.setattr("openwfn.ingest._load_iodata", fake_backend)
    source = tmp_path / "water.cp2k.out"
    source.write_text("CP2K| version string: CP2K version 2026\n", encoding="utf-8")

    load_input(source)

    assert calls == ["cp2klog"]


def test_explicit_qcschema_hint_routes_to_backend(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_backend(_path: Path, *, format_id: str) -> OpenWFNData:
        calls.append(format_id)
        return OpenWFNData(None, None, None, (), None, SourceMetadata(), None)

    monkeypatch.setattr("openwfn.ingest._load_iodata", fake_backend)
    source = tmp_path / "result.json"
    source.write_text("{}", encoding="utf-8")

    load_input(source, format_hint="json_qcschema")

    assert calls == ["json_qcschema"]


def test_backend_format_without_interop_extra_has_actionable_error(monkeypatch, tmp_path: Path) -> None:
    from openwfn import ingest
    from openwfn.errors import MissingOptionalDependencyError

    actual_import = ingest.import_module

    def import_without_backend(name: str):
        if name == "iodata":
            raise ModuleNotFoundError("No module named 'iodata'")
        return actual_import(name)

    monkeypatch.setattr(ingest, "import_module", import_without_backend)

    source = tmp_path / "water.molden"
    source.write_text("[Molden Format]\n", encoding="utf-8")

    with pytest.raises(MissingOptionalDependencyError, match=r'pip install "openwfn\[interop\]"'):
        load_input(source)


def test_unknown_format_does_not_try_arbitrary_parser(tmp_path: Path) -> None:
    source = tmp_path / "unknown.zzz"
    source.write_text("1\nlooks vaguely like data\nO 0 0 0\n", encoding="utf-8")

    with pytest.raises(ParseError, match="Unsupported input format"):
        load_input(source)


def test_two_record_xyz_is_not_silently_concatenated(tmp_path: Path) -> None:
    source = tmp_path / "trajectory.xyz"
    source.write_text(
        "1\nframe 1\nH 0 0 0\n1\nframe 2\nH 1 0 0\n",
        encoding="utf-8",
    )

    with pytest.raises(ParseError, match=r"sequence/trajectory ingestion is not part of the 0.9 load\(\) API"):
        load_input(source)


def test_suffixed_vasp_fixtures_route() -> None:
    pytest.importorskip("iodata", reason="requires the optional interoperability backend")
    root = Path(__file__).resolve().parents[1] / "fixtures" / "interop"
    for directory, filename, expected in (
        ("chgcar", "CHGCAR-water", "chgcar"),
        ("locpot", "LOCPOT-water", "locpot"),
        ("poscar", "POSCAR-water", "poscar"),
    ):
        loaded = load_input(root / directory / filename)
        assert loaded.provenance is not None
        assert loaded.provenance.source_format == expected
