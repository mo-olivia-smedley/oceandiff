"""
oceandiff.diff.diff
-------------------
Ocean-specific difference computation between two NetCDF files.
"""

from __future__ import annotations
import logging
import xarray as xr
import numpy as np

logger = logging.getLogger(__name__)


def _check_time_variables(ds1: xr.Dataset, ds2: xr.Dataset) -> None:
    """
    Check for differences in time and time_bounds variables across files.
    Logs warnings if variables exist in both files but differ.
    Checks both coordinates and data variables.
    """
    time_vars = ["time", "time_bounds"]

    for var in time_vars:
        # Check both coords and data_vars
        has_v1 = var in ds1.coords or var in ds1.data_vars
        has_v2 = var in ds2.coords or var in ds2.data_vars

        if has_v1 and has_v2:
            v1 = ds1[var]
            v2 = ds2[var]

            # Check shape
            if v1.shape != v2.shape:
                logger.warning(
                    "Variable '%s' shape differs: %s vs %s",
                    var,
                    v1.shape,
                    v2.shape,
                )
                continue

            # Check data values with strict tolerance for time
            try:
                # Use stricter/exact comparison for time variables
                if np.issubdtype(v1.dtype, np.datetime64) and np.issubdtype(
                    v2.dtype, np.datetime64
                ):
                    # For datetime, require exact match
                    if not np.array_equal(v1.values, v2.values, equal_nan=True):
                        logger.warning(
                            "Variable '%s' datetime values differ:\n"
                            "  File1: %s\n"
                            "  File2: %s",
                            var,
                            v1.values,
                            v2.values,
                        )
                else:
                    # For numeric time, use smaller tolerance
                    if not np.allclose(
                        v1.values, v2.values, rtol=1e-9, atol=1e-12, equal_nan=True
                    ):
                        max_diff = float(np.nanmax(np.abs(v1.values - v2.values)))
                        logger.warning(
                            "Variable '%s' values differ (max diff: %s):\n"
                            "  File1: %s\n"
                            "  File2: %s",
                            var,
                            max_diff,
                            v1.values,
                            v2.values,
                        )
            except (TypeError, ValueError) as e:
                logger.warning("Variable '%s' values could not be compared: %s", var, e)

            # Check attributes
            if v1.attrs != v2.attrs:
                logger.warning(
                    "Variable '%s' attributes differ: %s vs %s",
                    var,
                    v1.attrs,
                    v2.attrs,
                )


def _coords_close(
    coords1: dict, coords2: dict, rtol: float = 1e-5, atol: float = 1e-8
) -> tuple[bool, str]:
    """Check if two coordinate dictionaries are close within tolerance.

    Returns (match: bool, reason: str).

    For datetime64 coordinates, converts to int64 (nanoseconds) and uses numeric tolerance.
    """
    if set(coords1.keys()) != set(coords2.keys()):
        return (
            False,
            f"coordinate names differ: {set(coords1.keys())} vs {set(coords2.keys())}",
        )

    for name in coords1:
        c1 = coords1[name]
        c2 = coords2[name]

        if c1.shape != c2.shape:
            return False, f"coordinate {name} shape differs: {c1.shape} vs {c2.shape}"

        # For numeric coordinates, use allclose with tolerance
        if np.issubdtype(c1.dtype, np.number) and np.issubdtype(c2.dtype, np.number):
            if not np.allclose(
                c1.values, c2.values, rtol=rtol, atol=atol, equal_nan=True
            ):
                max_diff = float(np.nanmax(np.abs(c1.values - c2.values)))
                return False, f"coordinate {name} values differ (max diff: {max_diff})"
        # For datetime64 coordinates, convert to int64 and compare numerically
        elif np.issubdtype(c1.dtype, np.datetime64) and np.issubdtype(
            c2.dtype, np.datetime64
        ):
            try:
                c1_int = c1.values.astype("int64")
                c2_int = c2.values.astype("int64")
                if not np.allclose(
                    c1_int, c2_int, rtol=rtol, atol=atol, equal_nan=True
                ):
                    max_diff = int(np.nanmax(np.abs(c1_int - c2_int)))
                    return (
                        False,
                        f"coordinate {name} (datetime) values differ (max diff: {max_diff} ns)",
                    )
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
    no_interp: bool = False,
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
    with xr.open_dataset(file1) as ds1, xr.open_dataset(file2) as ds2:
        result = _compute_diff(ds1, ds2, var1, var2, time, depth, no_interp)
        # Load data into memory before datasets are closed
        result.load()
    return result


def _compute_diff(
    ds1: xr.Dataset,
    ds2: xr.Dataset,
    var1: str,
    var2: str,
    time: int | None,
    depth: int | None,
    no_interp: bool,
) -> xr.DataArray:
    # Check time and time_bounds variables first
    _check_time_variables(ds1, ds2)

    # Extract variables
    da1 = ds1[var1]
    da2 = ds2[var2]

    # Diagnostic: log coordinate info before interpolation
    logger.debug("File1 %s: dims=%s, shape=%s", var1, da1.dims, da1.shape)
    for coord_name in da1.dims:
        if coord_name in da1.coords:
            coord = da1.coords[coord_name]
            c_min = float(coord.values.min()) if coord.size > 0 else float("nan")
            c_max = float(coord.values.max()) if coord.size > 0 else float("nan")
            logger.debug(
                "  %s: size=%d, range=[%.6g, %.6g]",
                coord_name,
                coord.size,
                c_min,
                c_max,
            )

    logger.debug("File2 %s: dims=%s, shape=%s", var2, da2.dims, da2.shape)
    for coord_name in da2.dims:
        if coord_name in da2.coords:
            coord = da2.coords[coord_name]
            c_min = float(coord.values.min()) if coord.size > 0 else float("nan")
            c_max = float(coord.values.max()) if coord.size > 0 else float("nan")
            logger.debug(
                "  %s: size=%d, range=[%.6g, %.6g]",
                coord_name,
                coord.size,
                c_min,
                c_max,
            )

    # Apply time and depth slicing BEFORE interpolation/subtraction
    # This ensures both variables are at the same time/depth index
    time_candidates = ["time", "time_counter", "t", "T"]
    depth_candidates = [
        "depth",
        "deptht",
        "depthu",
        "depthv",
        "depthw",
        "z",
        "lev",
        "level",
    ]

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
            logger.debug("Grids match (lenient): %s; no interpolation needed.", reason)
        else:
            if no_interp:
                raise ValueError(
                    f"Grids differ and --no-interp is set.\n"
                    f"Reason: {reason}\n"
                    f"File1 {var1}: dims={da1.dims}, shape={da1.shape}\n"
                    f"File2 {var2}: dims={da2.dims}, shape={da2.shape}"
                )
            logger.info("Grids differ (%s); attempting interpolation...", reason)
            da2 = da2.interp_like(da1)
    else:
        logger.debug("Grids match (exact); no interpolation needed.")

    # Subtract
    diff = da1 - da2
    diff.name = f"{var1}_minus_{var2}"

    return diff
