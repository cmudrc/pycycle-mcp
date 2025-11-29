"""CLI entrypoint for running the pyCycle FastMCP server."""

from __future__ import annotations

import argparse
import logging

from fastmcp.server.server import Transport

from .fastmcp_server import build_server


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the pyCycle MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "http"],
        default="stdio",
        help="Transport to expose (http is treated as streamable-http)",
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host for HTTP-based transports"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP-based transports",
    )
    parser.add_argument(
        "--path",
        "--streamable-http-path",
        dest="path",
        default="/mcp",
        help="Endpoint path for HTTP/streamable-http transports",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Backward-compatible no-op flag from the legacy CLI",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (e.g. INFO, DEBUG)",
    )
    return parser.parse_args(argv)


def _normalize_transport(raw_transport: str) -> Transport:
    if raw_transport == "http":
        return "streamable-http"
    return raw_transport  # type: ignore[return-value]


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    if args.serve:
        logging.getLogger(__name__).info(
            "--serve is accepted for compatibility and can be omitted."
        )

    transport: Transport = _normalize_transport(args.transport)

    server = build_server()
    server.run(
        transport=transport,
        host=args.host,
        port=args.port,
        path=args.path,
        show_banner=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
