from __future__ import annotations

import anyio

from pycycle_mcp_server import fastmcp_server
from pycycle_mcp_server.main import cli


def test_build_server_exposes_schemas() -> None:
    server = fastmcp_server.build_server()
    tool = anyio.run(server.get_tool, "compute_totals")

    assert tool.output_schema["type"] == "object"
    assert "jacobian" in tool.output_schema.get("properties", {})


def test_create_cycle_model_wrapper_returns_structured(monkeypatch) -> None:
    def fake_create(payload: dict[str, object]) -> dict[str, object]:
        assert payload["cycle_type"] == "custom"
        return {
            "session_id": "abc123",
            "model_name": "demo",
            "top_promoted_inputs": [],
            "top_promoted_outputs": [],
        }

    monkeypatch.setattr(
        fastmcp_server.tools.create_model, "create_cycle_model", fake_create
    )
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

    assert result.structured_content["session_id"] == "abc123"
    assert result.structured_content["model_name"] == "demo"


def test_cli_lists_fastmcp_tools(capsys) -> None:
    exit_code = cli(["--list-tools"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "create_cycle_model" in captured.out
