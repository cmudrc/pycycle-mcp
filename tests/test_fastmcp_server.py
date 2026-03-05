from __future__ import annotations

import anyio
from pytest import MonkeyPatch

from pycycle_mcp import fastmcp_server


def test_build_server_exposes_schemas() -> None:
    server = fastmcp_server.build_server()

    tool = anyio.run(server.get_tool, "compute_totals")

    assert tool.output_schema is not None
    assert tool.output_schema["type"] == "object"
    assert "jacobian" in tool.output_schema.get("properties", {})


def test_ping_tool_is_registered() -> None:
    server = fastmcp_server.build_server()

    tool = anyio.run(server.get_tool, "ping")
    result = anyio.run(tool.run, {})

    assert result.structured_content is not None
    assert result.structured_content["server"] == "pycycle-mcp"


def test_create_cycle_model_wrapper_returns_structured(
    monkeypatch: MonkeyPatch,
) -> None:
    def fake_create(payload: dict[str, object]) -> dict[str, object]:
        assert payload["cycle_type"] == "custom"
        return {
            "session_id": "abc123",
            "model_name": "demo",
            "top_promoted_inputs": [],
            "top_promoted_outputs": [],
        }

    monkeypatch.setattr(fastmcp_server.tools.create_model, "create_cycle_model", fake_create)
    server = fastmcp_server.build_server()
    tool = anyio.run(server.get_tool, "create_cycle_model")

    result = anyio.run(
        tool.run,
        {
            "cycle_type": "custom",
            "mode": "design",
            "cycle_module_path": "tests.test_create_model.dummy_builder",
            "options": {},
        },
    )

    assert result.structured_content is not None
    assert result.structured_content["session_id"] == "abc123"
    assert result.structured_content["model_name"] == "demo"


def test_all_tool_wrappers_return_validated_structured_content(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        fastmcp_server.tools.create_model,
        "close_cycle_model",
        lambda payload: {"success": True},
    )
    monkeypatch.setattr(
        fastmcp_server.tools.create_model,
        "get_cycle_summary",
        lambda payload: {
            "model_name": "demo",
            "mode": "design",
            "options": {},
            "key_inputs": [],
            "key_outputs": [],
        },
    )
    monkeypatch.setattr(
        fastmcp_server.tools.variables,
        "list_variables",
        lambda payload: {"variables": []},
    )
    monkeypatch.setattr(
        fastmcp_server.tools.variables,
        "set_inputs",
        lambda payload: {"updated": [], "skipped": []},
    )
    monkeypatch.setattr(
        fastmcp_server.tools.variables,
        "get_outputs",
        lambda payload: {"values": {}, "missing": []},
    )
    monkeypatch.setattr(
        fastmcp_server.tools.execution,
        "run_cycle",
        lambda payload: {"success": True, "outputs": {}, "messages": []},
    )
    monkeypatch.setattr(
        fastmcp_server.tools.sweep,
        "sweep_inputs",
        lambda payload: {"results": []},
    )
    monkeypatch.setattr(
        fastmcp_server.tools.derivatives,
        "compute_totals",
        lambda payload: {"jacobian": {}, "messages": []},
    )

    server = fastmcp_server.build_server()

    close_tool = anyio.run(server.get_tool, "close_cycle_model")
    summary_tool = anyio.run(server.get_tool, "get_cycle_summary")
    list_tool = anyio.run(server.get_tool, "list_variables")
    set_tool = anyio.run(server.get_tool, "set_inputs")
    get_tool = anyio.run(server.get_tool, "get_outputs")
    run_tool = anyio.run(server.get_tool, "run_cycle")
    sweep_tool = anyio.run(server.get_tool, "sweep_inputs")
    totals_tool = anyio.run(server.get_tool, "compute_totals")

    assert anyio.run(close_tool.run, {"session_id": "s"}).structured_content == {"success": True}
    assert anyio.run(summary_tool.run, {"session_id": "s"}).structured_content == {
        "model_name": "demo",
        "mode": "design",
        "options": {},
        "key_inputs": [],
        "key_outputs": [],
    }
    assert anyio.run(
        list_tool.run,
        {"session_id": "s", "kind": "both", "promoted_only": True, "max_variables": 5},
    ).structured_content == {"variables": []}
    assert anyio.run(
        set_tool.run,
        {"session_id": "s", "values": {"Mach": 0.8}, "allow_missing": True},
    ).structured_content == {"updated": [], "skipped": []}
    assert anyio.run(get_tool.run, {"session_id": "s", "names": ["Fn"], "allow_missing": True}).structured_content == {
        "values": {},
        "missing": [],
    }
    assert anyio.run(
        run_tool.run,
        {"session_id": "s", "outputs_of_interest": ["Fn"], "use_driver": False},
    ).structured_content == {"success": True, "outputs": {}, "messages": []}
    assert anyio.run(
        sweep_tool.run,
        {
            "session_id": "s",
            "sweep": [{"name": "Mach", "values": [0.7, 0.8]}],
            "outputs_of_interest": ["Fn"],
            "use_driver": False,
            "skip_on_failure": True,
        },
    ).structured_content == {"results": []}
    assert anyio.run(
        totals_tool.run,
        {"session_id": "s", "of": ["Fn"], "wrt": ["Mach"], "return_format": "by_pair"},
    ).structured_content == {"jacobian": {}, "messages": []}
