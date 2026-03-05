"""List the current pyCycle MCP tools using the in-process FastMCP app."""

from __future__ import annotations

import json

import anyio

from pycycle_mcp.fastmcp_server import build_server


def _collect_tools() -> dict[str, object]:
    """Collect tool metadata in a stable JSON shape."""
    server = build_server()
    tools = anyio.run(server.get_tools)
    tool_names = sorted(tool.name for tool in tools.values())
    return {
        "tool_count": len(tool_names),
        "tool_names": tool_names,
    }


def main() -> None:
    """Print discovered tool names as JSON."""
    print(json.dumps(_collect_tools(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
