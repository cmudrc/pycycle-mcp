"""Entry point for the pyCycle MCP FastMCP server."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Any, Literal, cast

from pycycle_mcp.fastmcp_server import build_server

TransportName = Literal["stdio", "http", "sse", "streamable-http"]


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the FastMCP server CLI."""
    parser = argparse.ArgumentParser(description="pyCycle MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "http", "sse", "streamable-http"),
        default="stdio",
        help=(
            "Transport for serving MCP (stdio for local/editor integrations, "
            "HTTP-compatible modes for network serving)."
        ),
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind for HTTP-compatible transports (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind for HTTP-compatible transports (default: 8000)",
    )
    parser.add_argument(
        "--path",
        help=("Optional path to mount the HTTP endpoint (defaults to FastMCP's protocol-specific path)."),
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level for server startup messages.",
    )
    return parser


def _normalize_transport(transport: TransportName) -> TransportName:
    """Normalize legacy HTTP aliasing used by existing integrations."""
    if transport == "http":
        return "streamable-http"
    return transport


def main(argv: Sequence[str] | None = None) -> int:
    """Register tools and start the FastMCP server."""
    parser = build_parser()
    args = parser.parse_args(argv)

    app = build_server()
    transport = _normalize_transport(cast(TransportName, args.transport))

    transport_kwargs: dict[str, Any] = {"show_banner": False}
    if transport in {"sse", "streamable-http"}:
        transport_kwargs["host"] = args.host
        transport_kwargs["port"] = args.port
        if args.path is not None:
            transport_kwargs["path"] = args.path

    app.run(transport=transport, **transport_kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
