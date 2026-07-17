"""
oceandiff.diff.stats
--------------------
Statistical summaries for ocean difference fields.
"""

from __future__ import annotations
import numpy as np
import xarray as xr


def diff_stats(diff: xr.DataArray) -> dict:
    """
    Compute summary statistics for a difference field.

    Parameters
    ----------
    diff : xarray.DataArray
        Difference field (e.g. output from diff_variable)

    Returns
    -------
    stats : dict
        Dictionary containing min, max, mean and RMS difference.
    """

    # Flatten and drop NaNs
    data = diff.values
    data = data[~np.isnan(data)]

    if data.size == 0:
        raise ValueError("Difference field contains only NaNs")

    stats = {
        "min": float(data.min()),
        "max": float(data.max()),
        "mean": float(data.mean()),
        "rms": float(np.sqrt((data**2).mean())),
    }

    return stats
