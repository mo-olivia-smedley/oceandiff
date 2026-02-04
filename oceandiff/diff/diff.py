"""
oceandiff.diff.diff
-------------------
Ocean-specific difference computation between two NetCDF files.
"""

from __future__ import annotations
import xarray as xr


def diff_variable(
    file1: str,
    file2: str,
    var1: str,
    var2: str | None = None,
    time: int | None = None,
    depth: int | None = None
) -> xr.DataArray:
    """
    Compute the difference between two variables in NetCDF files.

    Parameters
    ----------
    file1 : str
        Path to first NetCDF file (e.g., EOS-80 dataset)
    file2 : str
        Path to second NetCDF file (e.g., TEOS-10 dataset)
    var1 : str
        Variable name in file1
    var2 : str, optional
        Variable name in file2. Defaults to same as var1.
    depth : int, optional
        Depth index to select. If None, keeps all depths.

    Returns
    -------
    diff : xarray.DataArray
        DataArray of the difference: var1(file1) - var2(file2)
    """

    if var2 is None:
        var2 = var1

    # Open datasets
    ds1 = xr.open_dataset(file1)
    ds2 = xr.open_dataset(file2)

    # Extract variables
    da1 = ds1[var1]
    da2 = ds2[var2]

    # Interpolate if grids differ
    if da1.dims != da2.dims or not da1.coords.equals(da2.coords):
        da2 = da2.interp_like(da1)

    # # Align coordinates (lat/lon/time/depth)
    # da1, da2 = xr.align(da1, da2, join="exact")

    # Subtract
    diff = da1 - da2
    diff.name = f"{var1}_minus_{var2}"

    # Handle time dimension only (keep spatial dims)
    if time is not None and "time" in diff.dims:
        diff = diff.isel(time=time)

    # Handle depth dimension if present
    if depth is not None and "depth" in diff.dims:
        diff = diff.isel(depth=depth)

    print("Difference dimensions:", diff.dims)
    print("Difference coordinates:", diff.coords)
    print("Difference attributes:", diff.attrs)

    # # Select depth if requested
    # if depth is not None and "depth" in da1.dims:
    #     da1 = da1.isel(depth=depth)
    #     da2 = da2.isel(depth=depth)

    # # Compute difference
    # diff = da1 - da2
    

    return diff

