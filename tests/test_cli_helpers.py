from __future__ import annotations

import argparse
import numpy as np
import pytest

from oceandiff.cli.main import (
    _build_pair_map,
    _infer_var_from_filename,
    _normalize_filename_for_pairing,
    _resolve_comparison_vars,
)
from conftest import make_2d_dataset, write_dataset


def test_infer_var_from_filename_with_default_pattern() -> None:
    path = "metoffice_foam1_amm15_NWS_TEM_b20260706_dm20260704.nc"
    assert _infer_var_from_filename(path) == "TEM"


def test_infer_var_from_filename_with_custom_regex() -> None:
    path = "foo_CUR_b20260706_dd20260704.nc"
    regex = r"^foo_(?P<var>[A-Z]+)_b\d+_d[a-z]\d+\.nc$"
    assert _infer_var_from_filename(path, filename_var_regex=regex) == "CUR"


def test_normalize_filename_for_pairing_merges_dm_and_dd() -> None:
    assert _normalize_filename_for_pairing("sample_dm20260704.nc") == "sample_d20260704.nc"
    assert _normalize_filename_for_pairing("sample_dd20260704.nc") == "sample_d20260704.nc"


def test_build_pair_map_raises_on_ambiguous_normalized_key(tmp_path) -> None:
    parser = argparse.ArgumentParser()

    p1 = tmp_path / "a_dm20260704.nc"
    p2 = tmp_path / "a_dd20260704.nc"
    p1.write_text("x")
    p2.write_text("x")

    files = {
        p1.name: p1,
        p2.name: p2,
    }

    with pytest.raises(SystemExit):
        _build_pair_map(files, str(tmp_path), None, parser, "--dir1")


def test_resolve_comparison_vars_uses_explicit_override(tmp_path) -> None:
    ds1 = make_2d_dataset("thetao", np.zeros((2, 3)))
    ds2 = make_2d_dataset("so", np.zeros((2, 3)))
    f1 = write_dataset(tmp_path, "a.nc", ds1)
    f2 = write_dataset(tmp_path, "b.nc", ds2)

    pairs, reason = _resolve_comparison_vars(f1, f2, category_hint=None, explicit_var1="thetao", explicit_var2="so")

    assert pairs == [("thetao", "so")]
    assert reason == "explicit variable thetao"


def test_resolve_comparison_vars_uses_category_hint_when_available(tmp_path) -> None:
    ds1 = make_2d_dataset("uo", np.zeros((2, 3)))
    ds1["vo"] = (("y", "x"), np.ones((2, 3)))
    ds1["thetao"] = (("y", "x"), np.ones((2, 3)))

    ds2 = make_2d_dataset("uo", np.zeros((2, 3)))
    ds2["vo"] = (("y", "x"), np.ones((2, 3)))
    ds2["thetao"] = (("y", "x"), np.ones((2, 3)))

    f1 = write_dataset(tmp_path, "a.nc", ds1)
    f2 = write_dataset(tmp_path, "b.nc", ds2)

    pairs, reason = _resolve_comparison_vars(f1, f2, category_hint="CUR", explicit_var1=None, explicit_var2=None)

    assert pairs == [("uo", "uo"), ("vo", "vo")]
    assert reason == "category CUR"


def test_resolve_comparison_vars_raises_when_no_common_variables(tmp_path) -> None:
    f1 = write_dataset(tmp_path, "a.nc", make_2d_dataset("thetao", np.zeros((2, 3))))
    f2 = write_dataset(tmp_path, "b.nc", make_2d_dataset("so", np.zeros((2, 3))))

    with pytest.raises(ValueError, match="No common data variables"):
        _resolve_comparison_vars(f1, f2, category_hint=None, explicit_var1=None, explicit_var2=None)
