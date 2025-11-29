from __future__ import annotations

import anyio
from pytest import MonkeyPatch

from pycycle_mcp_server import __main__ as cli
from pycycle_mcp_server import fastmcp_server


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

    assert result.structured_content is not None
    assert result.structured_content["session_id"] == "abc123"
    assert result.structured_content["model_name"] == "demo"


def test_main_normalizes_http_transport(monkeypatch: MonkeyPatch) -> None:
    recorded: list[dict[str, object]] = []

    class DummyServer:
        def run(
            self, **kwargs: object
        ) -> None:  # pragma: no cover - simple data capture
            recorded.append(kwargs)

    monkeypatch.setattr(cli, "build_server", lambda: DummyServer())

    exit_code = cli.main(
        ["--transport", "http", "--host", "0.0.0.0", "--port", "9001", "--path", "/mcp"]
    )

    assert exit_code == 0
    assert recorded == [
        {
            "transport": "streamable-http",
            "host": "0.0.0.0",
            "port": 9001,
            "path": "/mcp",
            "show_banner": False,
        }
    ]
