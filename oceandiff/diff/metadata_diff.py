"""
oceandiff.diff.metadata_diff
----------------------------
Compare metadata between two NetCDF files.

This includes:
- Global attributes
- Variable-level attributes
"""

from __future__ import annotations
import xarray as xr


def _diff_dict(d1: dict, d2: dict) -> dict:
    """
    Compare two dictionaries and return differences.
    """
    diffs = {}

    keys = set(d1.keys()) | set(d2.keys())

    for k in keys:
        v1 = d1.get(k, "<MISSING>")
        v2 = d2.get(k, "<MISSING>")

        if v1 != v2:
            diffs[k] = {"file1": v1, "file2": v2}

    return diffs


def diff_global_metadata(file1: str, file2: str) -> dict:
    """
    Compare global attributes between two NetCDF files.
    """

    ds1 = xr.open_dataset(file1)
    ds2 = xr.open_dataset(file2)

    return _diff_dict(ds1.attrs, ds2.attrs)


def diff_variable_metadata(
    file1: str,
    file2: str,
    variables: list[str] | None = None,
) -> dict:
    """
    Compare variable-level attributes between two NetCDF files.

    Parameters
    ----------
    file1, file2 : str
        NetCDF files to compare
    variables : list of str, optional
        Variables to compare. If None, compares common variables.

    Returns
    -------
    dict
        Nested dictionary of attribute differences.
    """

    ds1 = xr.open_dataset(file1)
    ds2 = xr.open_dataset(file2)

    if variables is None:
        variables = sorted(set(ds1.data_vars) & set(ds2.data_vars))

    diffs = {}

    for var in variables:
        attrs1 = ds1[var].attrs
        attrs2 = ds2[var].attrs

        var_diffs = _diff_dict(attrs1, attrs2)

        if var_diffs:
            diffs[var] = var_diffs

    return diffs
