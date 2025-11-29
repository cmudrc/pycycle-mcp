"""Entry point for the pyCycle MCP server.

This module provides a lightweight CLI interface for invoking the MCP tools
individually. A full MCP host can import the tool functions and schemas from
:mod:`pycycle_mcp_server.tools`.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Callable

from .tools import create_model, derivatives, execution, sweep, variables

LOGGER = logging.getLogger(__name__)


TOOL_DISPATCH: dict[str, Callable[[dict[str, object]], dict[str, object]]] = {
    "create_cycle_model": create_model.create_cycle_model,
    "close_cycle_model": create_model.close_cycle_model,
    "get_cycle_summary": create_model.get_cycle_summary,
    "list_variables": variables.list_variables,
    "set_inputs": variables.set_inputs,
    "get_outputs": variables.get_outputs,
    "run_cycle": execution.run_cycle,
    "sweep_inputs": sweep.sweep_inputs,
    "compute_totals": derivatives.compute_totals,
}


TOOL_DESCRIPTIONS: dict[str, str] = {
    name: func.__doc__.splitlines()[0] if func.__doc__ else ""
    for name, func in TOOL_DISPATCH.items()
}


def run_tool(tool_name: str, payload: dict[str, object]) -> dict[str, object]:
    """Execute a tool by name with a JSON-compatible payload."""

    handler = TOOL_DISPATCH.get(tool_name)
    if handler is None:
        return {
            "error": {"type": "UnknownTool", "message": f"Unknown tool: {tool_name}"}
        }
    return handler(payload)


def cli(argv: list[str] | None = None) -> int:
    """Simple CLI for invoking tools manually."""

    parser = argparse.ArgumentParser(description="pyCycle MCP server utility CLI")
    parser.add_argument(
        "--tool", choices=sorted(TOOL_DISPATCH.keys()), help="Tool to invoke"
    )
    parser.add_argument("--payload", help="JSON payload for the tool")
    parser.add_argument(
        "--list-tools", action="store_true", help="List available tools and exit"
    )

    args = parser.parse_args(argv)

    if args.list_tools:
        for name in sorted(TOOL_DISPATCH):
            description = TOOL_DESCRIPTIONS.get(name, "")
            print(f"{name}: {description}")
        return 0

    if not args.tool:
        parser.error("--tool is required unless --list-tools is provided")

    payload_data: dict[str, object] = {}
    if args.payload:
        payload_data = json.loads(args.payload)

    response = run_tool(args.tool, payload_data)
    print(json.dumps(response, indent=2, default=str))
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cli()
