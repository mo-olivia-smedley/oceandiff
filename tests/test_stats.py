from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from oceandiff.diff.stats import diff_stats


def test_diff_stats_computes_expected_values() -> None:
    diff = xr.DataArray(np.array([1.0, -1.0, 2.0, np.nan]))

    stats = diff_stats(diff)

    assert stats["min"] == -1.0
    assert stats["max"] == 2.0
    assert stats["mean"] == pytest.approx(2.0 / 3.0)
    assert stats["rms"] == pytest.approx((2.0) ** 0.5)


def test_diff_stats_raises_for_all_nan() -> None:
    diff = xr.DataArray(np.array([np.nan, np.nan]))

    with pytest.raises(ValueError, match="only NaNs"):
        diff_stats(diff)
