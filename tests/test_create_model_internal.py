from __future__ import annotations

import sys
import types

import pytest

from pycycle_mcp.tools import create_model


class _RecorderProblem:
    def __init__(self) -> None:
        self.model: object | None = None
        self.setup_calls: list[bool] = []
        self.set_calls: list[tuple[str, object, object | None]] = []
        self.item_calls: dict[str, object] = {}

    def setup(self, check: bool = False) -> None:
        self.setup_calls.append(check)

    def set_val(
        self,
        name: str | None = None,
        value: object | None = None,
        **kwargs: object,
    ) -> None:
        if name == "bad":
            raise RuntimeError("bad set")
        units = kwargs.get("units")
        if name is not None:
            self.set_calls.append((name, value, units))

    def __setitem__(self, name: str, value: object) -> None:
        self.item_calls[name] = value


def _install_fake_cycle_modules(monkeypatch: pytest.MonkeyPatch) -> tuple[type[object], type[object]]:
    pycycle_module = types.ModuleType("pycycle")
    pycycle_api_module = types.ModuleType("pycycle.api")
    pycycle_module.api = pycycle_api_module

    hb_module = types.ModuleType("pycycle_mcp.cycles.high_bypass_turbofan")

    class HBTF:
        def __init__(self, thermo_method: str | None = None) -> None:
            self.thermo_method = thermo_method

    hb_module.HBTF = HBTF

    tj_module = types.ModuleType("pycycle_mcp.cycles.simple_turbojet")

    class Turbojet:
        pass

    tj_module.Turbojet = Turbojet

    monkeypatch.setitem(sys.modules, "pycycle", pycycle_module)
    monkeypatch.setitem(sys.modules, "pycycle.api", pycycle_api_module)
    monkeypatch.setitem(sys.modules, "pycycle_mcp.cycles.high_bypass_turbofan", hb_module)
    monkeypatch.setitem(sys.modules, "pycycle_mcp.cycles.simple_turbojet", tj_module)

    return HBTF, Turbojet


def test_resolve_builtin_cycle_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(sys.modules, "pycycle", raising=False)
    monkeypatch.delitem(sys.modules, "pycycle.api", raising=False)

    with pytest.raises(ImportError):
        create_model._resolve_builtin_cycle("turbofan")


def test_resolve_builtin_cycle_success_and_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    hbtf_cls, turbojet_cls = _install_fake_cycle_modules(monkeypatch)

    cycle_type, turbofan_builder = create_model._resolve_builtin_cycle("turbofan")
    assert cycle_type == "turbofan"
    turbofan = turbofan_builder()
    assert isinstance(turbofan, hbtf_cls)
    assert turbofan.thermo_method == "CEA"

    cycle_type, turbojet_builder = create_model._resolve_builtin_cycle("turbojet")
    assert cycle_type == "turbojet"
    assert isinstance(turbojet_builder(), turbojet_cls)

    with pytest.raises(ValueError):
        create_model._resolve_builtin_cycle("unsupported")


def test_apply_design_defaults_for_both_builtin_cycle_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hbtf_cls, turbojet_cls = _install_fake_cycle_modules(monkeypatch)

    hbtf_problem = _RecorderProblem()
    create_model._apply_design_defaults(hbtf_problem, hbtf_cls(), mode="design")
    assert any(name == "fan.PR" for name, _, _ in hbtf_problem.set_calls)
    assert hbtf_problem.item_calls["balance.FAR"] == 0.025

    turbojet_problem = _RecorderProblem()
    create_model._apply_design_defaults(turbojet_problem, turbojet_cls(), mode="design")
    assert any(name == "comp.PR" for name, _, _ in turbojet_problem.set_calls)
    assert turbojet_problem.item_calls["balance.turb_PR"] == 4.46


class _FakeModel:
    pass


class _OpenMDAOProblem(_RecorderProblem):
    pass


def test_build_problem_import_error_when_openmdao_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(sys.modules, "openmdao", raising=False)
    monkeypatch.delitem(sys.modules, "openmdao.api", raising=False)

    with pytest.raises(ImportError):
        create_model._build_problem(lambda: _FakeModel(), "design", {})


def test_build_problem_success_and_option_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    openmdao_module = types.ModuleType("openmdao")
    openmdao_api_module = types.ModuleType("openmdao.api")
    openmdao_api_module.Problem = _OpenMDAOProblem
    openmdao_module.api = openmdao_api_module

    monkeypatch.setitem(sys.modules, "openmdao", openmdao_module)
    monkeypatch.setitem(sys.modules, "openmdao.api", openmdao_api_module)
    monkeypatch.setattr(create_model, "_apply_design_defaults", lambda problem, model, mode: None)

    problem, model_name = create_model._build_problem(
        lambda: _FakeModel(),
        mode="design",
        options={"good": 1.0, "bad": 2.0},
    )

    assert model_name == "_FakeModel"
    assert problem.setup_calls == [False]
    assert ("good", 1.0, None) in problem.set_calls


def test_close_cycle_model_success_path() -> None:
    response = create_model.close_cycle_model({"session_id": "anything"})
    assert response == {"success": True}
