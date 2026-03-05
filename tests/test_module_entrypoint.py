from __future__ import annotations

import runpy

import pytest

from pycycle_mcp import main as server_main


def test_python_m_entrypoint_exits_with_main_return_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server_main, "main", lambda: 7)

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("pycycle_mcp.__main__", run_name="__main__")

    assert exc.value.code == 7
