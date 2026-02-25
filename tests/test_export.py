import numpy as np  # type: ignore
import pytest  # type: ignore

from openwfn.export import export_vtk  # type: ignore


def test_export_vtk_writes_actual_spacing(tmp_path):
    x = np.array([0.0, 0.5])
    y = np.array([1.0, 1.25])
    z = np.array([-1.0, -0.9, -0.8])
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")
    points = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    shape = X.shape
    data = np.zeros(points.shape[0])

    out = tmp_path / "grid.vtk"
    export_vtk(str(out), points, shape, data)

    content = out.read_text()
    spacing_line = next(line for line in content.splitlines() if line.startswith("SPACING"))
    _, sx, sy, sz = spacing_line.split()
    assert float(sx) == pytest.approx(0.5)
    assert float(sy) == pytest.approx(0.25)
    assert float(sz) == pytest.approx(0.1)


def test_export_vtk_rejects_size_mismatch(tmp_path):
    points = np.array([[0.0, 0.0, 0.0]])
    data = np.array([0.0, 1.0])
    with pytest.raises(ValueError, match="data size does not match"):
        export_vtk(str(tmp_path / "bad.vtk"), points, (1, 1, 1), data)
