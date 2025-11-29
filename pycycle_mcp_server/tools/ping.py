"""Lightweight healthcheck tool for the pyCycle MCP server."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PingRequest(BaseModel):
    """Request payload for the :func:`ping` tool."""

    message: str | None = Field(
        default=None, description="Optional echo message included in the response."
    )


class PingResponse(BaseModel):
    """Response payload for the :func:`ping` tool."""

    server: str = Field(default="pycycle-mcp", description="Server identifier.")
    status: str = Field(default="ok", description="Simple health indicator.")
    message: str | None = Field(
        default=None,
        description="Optional echo message provided by the caller, if any.",
    )


def ping(args: PingRequest | None = None) -> PingResponse:
    """Return a simple health response without importing heavy dependencies."""

    args = args or PingRequest()
    return PingResponse(message=args.message)
