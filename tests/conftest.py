from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr


def write_dataset(tmp_path: Path, name: str, ds: xr.Dataset) -> str:
    """Write a dataset to a NetCDF file in the test temp directory."""
    path = tmp_path / name
    ds.to_netcdf(path)
    return str(path)


def make_2d_dataset(
    var_name: str,
    values: np.ndarray,
    x: np.ndarray | None = None,
    y: np.ndarray | None = None,
    attrs: dict | None = None,
    var_attrs: dict | None = None,
) -> xr.Dataset:
    """Create a small 2D dataset with x/y coordinates for testing."""
    if x is None:
        x = np.array([0.0, 1.0, 2.0])
    if y is None:
        y = np.array([10.0, 20.0])

    ds = xr.Dataset(
        data_vars={
            var_name: (("y", "x"), values),
        },
        coords={
            "x": x,
            "y": y,
        },
        attrs=attrs or {},
    )

    if var_attrs:
        ds[var_name].attrs.update(var_attrs)

    return ds


def make_4d_dataset(var_name: str, values: np.ndarray) -> xr.Dataset:
    """Create a 4D test dataset with time/depth/y/x dimensions."""
    time = np.array([0, 1])
    depth = np.array([5.0, 15.0])
    y = np.array([10.0, 20.0])
    x = np.array([0.0, 1.0, 2.0])

    return xr.Dataset(
        data_vars={
            var_name: (("time", "depth", "y", "x"), values),
        },
        coords={
            "time": time,
            "depth": depth,
            "y": y,
            "x": x,
        },
    )
