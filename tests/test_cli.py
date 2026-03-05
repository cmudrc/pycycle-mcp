"""CLI contract tests for the pyCycle MCP server entrypoints."""

from __future__ import annotations

import pytest

from pycycle_mcp import main as server_main


class _DummyApp:
    """Shim FastMCP app to capture run invocations without network I/O."""

    def __init__(self) -> None:
        self.run_calls: list[dict[str, object]] = []

    def add_tool(self, _: object) -> None:  # pragma: no cover - compatibility shim
        return

    def run(self, *, transport: str, **kwargs: object) -> None:
        """Capture transport arguments passed by the CLI."""
        self.run_calls.append({"transport": transport, **kwargs})


def test_build_parser_defaults_to_stdio_transport() -> None:
    """The CLI defaults to the local stdio transport."""
    parser = server_main.build_parser()
    args = parser.parse_args([])

    assert args.transport == "stdio"
    assert args.host == "0.0.0.0"
    assert args.port == 8000
    assert args.path is None


def test_main_runs_fastmcp_with_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() delegates to FastMCP.run with normalized transport settings."""
    dummy_app = _DummyApp()
    monkeypatch.setattr(server_main, "build_server", lambda: dummy_app)

    exit_code = server_main.main(
        [
            "--transport",
            "http",
            "--host",
            "127.0.0.1",
            "--port",
            "8080",
            "--path",
            "/mcp",
        ]
    )

    assert exit_code == 0
    assert dummy_app.run_calls == [
        {
            "transport": "streamable-http",
            "host": "127.0.0.1",
            "port": 8080,
            "path": "/mcp",
            "log_level": "INFO",
            "show_banner": False,
        }
    ]


def test_main_stdio_uses_non_network_transport_kwargs(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_app = _DummyApp()
    monkeypatch.setattr(server_main, "build_server", lambda: dummy_app)

    exit_code = server_main.main(["--transport", "stdio"])

    assert exit_code == 0
    assert dummy_app.run_calls == [{"transport": "stdio", "show_banner": False, "log_level": "INFO"}]


def test_main_forwards_custom_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_app = _DummyApp()
    monkeypatch.setattr(server_main, "build_server", lambda: dummy_app)

    exit_code = server_main.main(["--transport", "sse", "--log-level", "DEBUG"])

    assert exit_code == 0
    assert dummy_app.run_calls == [
        {
            "transport": "sse",
            "host": "0.0.0.0",
            "port": 8000,
            "show_banner": False,
            "log_level": "DEBUG",
        }
    ]
