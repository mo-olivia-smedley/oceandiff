from __future__ import annotations

import numpy as np

from oceandiff.diff.metadata_diff import diff_global_metadata, diff_variable_metadata
from conftest import make_2d_dataset, write_dataset


def test_diff_global_metadata_reports_changes_and_missing_keys(tmp_path) -> None:
    ds1 = make_2d_dataset(
        "thetao", np.zeros((2, 3)), attrs={"title": "run_a", "source": "model"}
    )
    ds2 = make_2d_dataset(
        "thetao", np.zeros((2, 3)), attrs={"title": "run_b", "history": "new"}
    )

    f1 = write_dataset(tmp_path, "a.nc", ds1)
    f2 = write_dataset(tmp_path, "b.nc", ds2)

    diffs = diff_global_metadata(f1, f2)

    assert diffs["title"] == {"file1": "run_a", "file2": "run_b"}
    assert diffs["source"] == {"file1": "model", "file2": "<MISSING>"}
    assert diffs["history"] == {"file1": "<MISSING>", "file2": "new"}


def test_diff_variable_metadata_for_common_vars(tmp_path) -> None:
    ds1 = make_2d_dataset(
        "thetao",
        np.zeros((2, 3)),
        var_attrs={"units": "degC", "long_name": "temperature"},
    )
    ds2 = make_2d_dataset(
        "thetao",
        np.zeros((2, 3)),
        var_attrs={"units": "K", "long_name": "temperature"},
    )

    f1 = write_dataset(tmp_path, "a.nc", ds1)
    f2 = write_dataset(tmp_path, "b.nc", ds2)

    diffs = diff_variable_metadata(f1, f2)

    assert "thetao" in diffs
    assert diffs["thetao"]["units"] == {"file1": "degC", "file2": "K"}
    assert "long_name" not in diffs["thetao"]


def test_diff_variable_metadata_respects_explicit_variable_list(tmp_path) -> None:
    ds1 = make_2d_dataset("thetao", np.zeros((2, 3)))
    ds1["so"] = (("y", "x"), np.ones((2, 3)))
    ds1["so"].attrs["units"] = "psu"

    ds2 = make_2d_dataset("thetao", np.zeros((2, 3)))
    ds2["so"] = (("y", "x"), np.ones((2, 3)))
    ds2["so"].attrs["units"] = "g/kg"

    f1 = write_dataset(tmp_path, "a.nc", ds1)
    f2 = write_dataset(tmp_path, "b.nc", ds2)

    diffs = diff_variable_metadata(f1, f2, variables=["so"])

    assert set(diffs.keys()) == {"so"}
    assert diffs["so"]["units"] == {"file1": "psu", "file2": "g/kg"}
