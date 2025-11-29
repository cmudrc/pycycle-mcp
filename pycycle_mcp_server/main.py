"""Entry point for the pyCycle FastMCP server."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Mapping
from typing import Any, Protocol

import anyio
from fastmcp.tools.tool import ToolResult

from .fastmcp_server import build_server
from .runtime import ServerSettings, configure_logging, run_server


class ToolLike(Protocol):
    """Minimal tool surface used for CLI rendering."""

    name: str
    description: str | None


def _render_tool_result(result: ToolResult) -> dict[str, Any]:
    """Convert a :class:`ToolResult` into a JSON-serializable mapping."""

    if result.structured_content is not None:
        return result.structured_content
    if isinstance(result.content, list):
        return {"content": [str(item) for item in result.content]}
    return {"content": result.content}


def _list_tools(server_output: Mapping[str, ToolLike] | Iterable[ToolLike]) -> None:
    tools = (
        server_output.values() if isinstance(server_output, Mapping) else server_output
    )
    for tool in tools:
        description = tool.description or ""
        print(f"{tool.name}: {description}")


def cli(argv: list[str] | None = None) -> int:
    """CLI for invoking FastMCP tools or running the server."""

    parser = argparse.ArgumentParser(description="pyCycle MCP server utility CLI")
    parser.add_argument("--tool", help="Tool to invoke")
    parser.add_argument("--payload", help="JSON payload for the tool")
    parser.add_argument(
        "--list-tools", action="store_true", help="List available tools and exit"
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Run the FastMCP server instead of invoking a single tool",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport to use when running the server",
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host for SSE/HTTP transports"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port for SSE/HTTP transports"
    )
    parser.add_argument(
        "--log-level", default="INFO", help="Logging level (e.g. INFO, DEBUG)"
    )

    args = parser.parse_args(argv)
    configure_logging(args.log_level)

    server = build_server()

    if args.list_tools:
        tools = anyio.run(server.get_tools)
        _list_tools(tools)
        return 0

    if args.serve:
        settings = ServerSettings(
            transport=args.transport, host=args.host, port=args.port, show_banner=False
        )
        run_server(server, settings)
        return 0

    if not args.tool:
        parser.error("--tool is required unless --list-tools or --serve is provided")

    payload_data: dict[str, Any] = {}
    if args.payload:
        payload_data = json.loads(args.payload)

    tool = anyio.run(server.get_tool, args.tool)
    tool_result = anyio.run(tool.run, payload_data)
    rendered_result = _render_tool_result(tool_result)
    print(json.dumps(rendered_result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    configure_logging()
    cli()
