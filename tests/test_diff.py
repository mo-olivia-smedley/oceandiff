from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from oceandiff.diff.diff import diff_variable
from conftest import make_2d_dataset, make_4d_dataset, write_dataset


def test_diff_variable_exact_grid_no_interpolation_needed(tmp_path) -> None:
    a = np.array([[2.0, 3.0, 4.0], [5.0, 6.0, 7.0]])
    b = np.array([[1.0, 1.0, 1.0], [1.0, 1.0, 1.0]])

    f1 = write_dataset(tmp_path, "a.nc", make_2d_dataset("thetao", a))
    f2 = write_dataset(tmp_path, "b.nc", make_2d_dataset("thetao", b))

    diff = diff_variable(f1, f2, "thetao")

    assert diff.name == "thetao_minus_thetao"
    assert diff.shape == (2, 3)
    assert np.allclose(diff.values, a - b)


def test_diff_variable_interpolates_when_grids_differ(tmp_path) -> None:
    # Grid 1: coarse sampling
    x1 = np.array([0.0, 1.0, 2.0])
    # Grid 2: finer sampling in same range, will be interpolated to coarse grid
    x2 = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
    y = np.array([10.0, 20.0])

    # Create data on grid 2 (finer)
    xx2, yy2 = np.meshgrid(x2, y)
    b = xx2 + yy2

    # Create dataset on grid 2
    ds2 = xr.Dataset({"thetao": (("y", "x"), b)}, coords={"x": x2, "y": y})

    # Create data on grid 1 (coarse) using same linear function
    xx1, yy1 = np.meshgrid(x1, y)
    a = xx1 + yy1
    ds1 = make_2d_dataset("thetao", a, x=x1, y=y)

    f1 = write_dataset(tmp_path, "a.nc", ds1)
    f2 = write_dataset(tmp_path, "b.nc", ds2)

    # Interpolate from finer grid to coarse grid
    diff = diff_variable(f1, f2, "thetao")

    assert diff.shape == (2, 3)
    # After interpolation of linear data, diff should be near zero
    assert np.allclose(diff.values, 0.0, atol=1e-5)


def test_diff_variable_raises_with_no_interp_on_grid_mismatch(tmp_path) -> None:
    f1 = write_dataset(tmp_path, "a.nc", make_2d_dataset("thetao", np.ones((2, 3))))
    f2 = write_dataset(
        tmp_path,
        "b.nc",
        make_2d_dataset("thetao", np.ones((2, 3)), x=np.array([0.2, 1.2, 2.2])),
    )

    with pytest.raises(ValueError, match="--no-interp"):
        diff_variable(f1, f2, "thetao", no_interp=True)


def test_diff_variable_applies_time_and_depth_selection(tmp_path) -> None:
    values1 = np.zeros((2, 2, 2, 3))
    values2 = np.zeros((2, 2, 2, 3))

    # Select time=1, depth=0 and make that slice differ by +3 everywhere.
    values1[1, 0, :, :] = 5.0
    values2[1, 0, :, :] = 2.0

    f1 = write_dataset(tmp_path, "a.nc", make_4d_dataset("thetao", values1))
    f2 = write_dataset(tmp_path, "b.nc", make_4d_dataset("thetao", values2))

    diff = diff_variable(f1, f2, "thetao", time=1, depth=0)

    assert diff.dims == ("y", "x")
    assert np.allclose(diff.values, 3.0)
