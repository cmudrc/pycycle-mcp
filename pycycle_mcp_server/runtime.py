"""Runtime utilities for configuring and running the FastMCP server."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from fastmcp.server import FastMCP


@dataclass
class ServerSettings:
    """Transport and networking configuration for FastMCP."""

    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000
    show_banner: bool = False


def configure_logging(level: int | str = logging.INFO) -> None:
    """Initialize logging for CLI and server runs."""

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def run_server(server: FastMCP, settings: ServerSettings) -> None:
    """Start the FastMCP server with the provided settings."""

    server.run(
        transport=settings.transport,
        host=settings.host,
        port=settings.port,
        show_banner=settings.show_banner,
    )
