from __future__ import annotations

import logging

from pycycle_mcp import runtime


class _DummyServer:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def run(self, **kwargs: object) -> None:
        self.calls.append(kwargs)


def test_run_server_passes_settings_to_fastmcp() -> None:
    server = _DummyServer()
    settings = runtime.ServerSettings(
        transport="streamable-http",
        host="0.0.0.0",
        port=9000,
        show_banner=True,
    )

    runtime.run_server(server, settings)

    assert server.calls == [
        {
            "transport": "streamable-http",
            "host": "0.0.0.0",
            "port": 9000,
            "show_banner": True,
        }
    ]


def test_configure_logging_uses_basic_config(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_basic_config(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(logging, "basicConfig", fake_basic_config)

    runtime.configure_logging("DEBUG")

    assert captured["level"] == "DEBUG"
    assert "%(asctime)s" in str(captured["format"])
