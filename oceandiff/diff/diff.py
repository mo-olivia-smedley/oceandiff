"""
oceandiff.diff.diff
-------------------
Ocean-specific difference computation between two NetCDF files.
"""

from __future__ import annotations
import xarray as xr
import numpy as np


def _coords_close(coords1: dict, coords2: dict, rtol: float = 1e-5, atol: float = 1e-8) -> tuple[bool, str]:
    """Check if two coordinate dictionaries are close within tolerance.
    
    Returns (match: bool, reason: str).
    
    For datetime64 coordinates, converts to int64 (nanoseconds) and uses numeric tolerance.
    """
    if set(coords1.keys()) != set(coords2.keys()):
        return False, f"coordinate names differ: {set(coords1.keys())} vs {set(coords2.keys())}"
    
    for name in coords1:
        c1 = coords1[name]
        c2 = coords2[name]
        
        if c1.shape != c2.shape:
            return False, f"coordinate {name} shape differs: {c1.shape} vs {c2.shape}"
        
        # For numeric coordinates, use allclose with tolerance
        if np.issubdtype(c1.dtype, np.number) and np.issubdtype(c2.dtype, np.number):
            if not np.allclose(c1.values, c2.values, rtol=rtol, atol=atol, equal_nan=True):
                max_diff = float(np.nanmax(np.abs(c1.values - c2.values)))
                return False, f"coordinate {name} values differ (max diff: {max_diff})"
        # For datetime64 coordinates, convert to int64 and compare numerically
        elif np.issubdtype(c1.dtype, np.datetime64) and np.issubdtype(c2.dtype, np.datetime64):
            try:
                c1_int = c1.values.astype('int64')
                c2_int = c2.values.astype('int64')
                if not np.allclose(c1_int, c2_int, rtol=rtol, atol=atol, equal_nan=True):
                    max_diff = int(np.nanmax(np.abs(c1_int - c2_int)))
                    return False, f"coordinate {name} (datetime) values differ (max diff: {max_diff} ns)"
            except Exception as e:
                return False, f"coordinate {name} (datetime) comparison failed: {e}"
        else:
            # For non-numeric (e.g., string) coordinates, require exact match
            if not np.array_equal(c1.values, c2.values, equal_nan=True):
                return False, f"coordinate {name} values differ (non-numeric)"
    
    return True, "all coordinates match"


def _find_dim(dims: tuple, candidates: list[str]) -> str | None:
    """Find the first matching dimension name from a list of candidates."""
    for candidate in candidates:
        if candidate in dims:
            return candidate
    return None


def diff_variable(
    file1: str,
    file2: str,
    var1: str,
    var2: str | None = None,
    time: int | None = None,
    depth: int | None = None,
    no_interp: bool = False
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
    time : int, optional
        Time index to select. If None, keeps all times.
    depth : int, optional
        Depth index to select. If None, keeps all depths.
    no_interp : bool, optional
        If True, skip interpolation and require exact grid match. Defaults to False.

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

    # Diagnostic: print coordinate info before interpolation
    print(f"File1 {var1}: dims={da1.dims}, shape={da1.shape}")
    for coord_name in da1.dims:
        if coord_name in da1.coords:
            coord = da1.coords[coord_name]
            c_min = float(coord.values.min()) if coord.size > 0 else float('nan')
            c_max = float(coord.values.max()) if coord.size > 0 else float('nan')
            print(f"  {coord_name}: size={coord.size}, range=[{c_min:.6g}, {c_max:.6g}]")

    print(f"File2 {var2}: dims={da2.dims}, shape={da2.shape}")
    for coord_name in da2.dims:
        if coord_name in da2.coords:
            coord = da2.coords[coord_name]
            c_min = float(coord.values.min()) if coord.size > 0 else float('nan')
            c_max = float(coord.values.max()) if coord.size > 0 else float('nan')
            print(f"  {coord_name}: size={coord.size}, range=[{c_min:.6g}, {c_max:.6g}]")

    # Apply time and depth slicing BEFORE interpolation/subtraction
    # This ensures both variables are at the same time/depth index
    time_candidates = ["time", "time_counter", "t", "T"]
    depth_candidates = ["depth", "deptht", "depthu", "depthv", "depthw", "z", "lev", "level"]

    if time is not None:
        time_dim = _find_dim(da1.dims, time_candidates)
        if time_dim is not None:
            da1 = da1.isel({time_dim: time})
        time_dim = _find_dim(da2.dims, time_candidates)
        if time_dim is not None:
            da2 = da2.isel({time_dim: time})

    if depth is not None:
        depth_dim = _find_dim(da1.dims, depth_candidates)
        if depth_dim is not None:
            da1 = da1.isel({depth_dim: depth})
        depth_dim = _find_dim(da2.dims, depth_candidates)
        if depth_dim is not None:
            da2 = da2.isel({depth_dim: depth})

    # Interpolate if grids differ (use lenient comparison for floating-point coordinates)
    exact_match = da1.dims == da2.dims and da1.coords.equals(da2.coords)
    if not exact_match:
        lenient_match, reason = _coords_close(da1.coords, da2.coords)
        if lenient_match:
            print(f"Grids match (lenient): {reason}; no interpolation needed.")
        else:
            if no_interp:
                raise ValueError(
                    f"Grids differ and --no-interp is set.\n"
                    f"Reason: {reason}\n"
                    f"File1 {var1}: dims={da1.dims}, shape={da1.shape}\n"
                    f"File2 {var2}: dims={da2.dims}, shape={da2.shape}"
                )
            print(f"Grids differ ({reason}); attempting interpolation...")
            da2 = da2.interp_like(da1)
    else:
        print("Grids match (exact); no interpolation needed.")

    # Subtract
    diff = da1 - da2
    diff.name = f"{var1}_minus_{var2}"

    return diff

