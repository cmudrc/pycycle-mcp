CLI and Transports
==================

The ``pycycle-mcp`` command and ``python -m pycycle_mcp`` entrypoint
both use ``pycycle_mcp.main``.

Supported transports
--------------------

- ``stdio`` for editor and local MCP integrations
- ``http`` (normalized to ``streamable-http`` for compatibility)
- ``sse`` for server-sent events
- ``streamable-http`` for FastMCP streamable HTTP mode

The parser defaults to ``stdio`` and only applies ``host``, ``port``, and
``path`` for HTTP-compatible transports.
