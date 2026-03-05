from __future__ import annotations

import sys
import types

import pytest

from pycycle_mcp import utils


def test_load_callable_invalid_path_and_non_callable(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ImportError):
        utils.load_callable("not_a_valid_path")

    fake_module = types.ModuleType("tests.fake_module_for_utils")
    fake_module.not_callable = 123
    monkeypatch.setitem(sys.modules, "tests.fake_module_for_utils", fake_module)

    with pytest.raises(TypeError):
        utils.load_callable("tests.fake_module_for_utils.not_callable")


def test_normalize_shape_and_cartesian_empty() -> None:
    assert utils._normalize_shape((2, 3)) == [2, 3]
    assert utils._normalize_shape(5) == 5
    assert utils.ordered_cartesian_product([]) == []
