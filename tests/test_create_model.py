from __future__ import annotations

from collections.abc import Callable
from typing import cast

import pytest

from pycycle_mcp_server.session_manager import session_manager
from pycycle_mcp_server.tools import create_model
from pycycle_mcp_server.types import CycleProblem

from .conftest import DummyModel, DummyProblem


def dummy_builder() -> DummyModel:
    return DummyModel(
        inputs=[("Mach", {"units": "", "desc": "Mach"})],
        outputs=[("Fn", {"units": "lbf"})],
    )


def test_create_cycle_model_custom(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_build_problem(
        builder: Callable[[], DummyModel], mode: str, options: dict[str, object]
    ) -> tuple[DummyProblem, str]:
        problem = DummyProblem()
        problem.model = builder()
        return problem, "dummy"

    monkeypatch.setattr(create_model, "_build_problem", fake_build_problem)

    response = create_model.create_cycle_model(
        {
            "cycle_type": "custom",
            "cycle_module_path": "tests.test_create_model.dummy_builder",
            "mode": "design",
            "options": {"Mach": 0.8},
        }
    )

    assert "session_id" in response
    assert response["model_name"] == "dummy"
    assert response["top_promoted_inputs"]
    assert response["top_promoted_outputs"]


def test_get_cycle_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    problem = DummyProblem()
    problem.model.inputs = [("alt", {"units": "ft", "desc": "Altitude", "val": 35000})]
    problem.model.outputs = [
        ("Fn", {"units": "lbf", "desc": "Net thrust", "val": 1000})
    ]
    session_id = session_manager.create_session(
        problem=cast(CycleProblem, problem), meta={"mode": "design", "options": {}}
    )

    response = create_model.get_cycle_summary({"session_id": session_id})
    key_inputs = cast(list[dict[str, object]], response["key_inputs"])
    key_outputs = cast(list[dict[str, object]], response["key_outputs"])
    assert response["model_name"] == "dummy"
    assert response["mode"] == "design"
    assert key_inputs[0]["name"] == "alt"
    assert key_outputs[0]["name"] == "Fn"


def test_create_cycle_model_missing_fields() -> None:
    response = create_model.create_cycle_model({"cycle_type": "turbofan"})
    assert "error" in response
