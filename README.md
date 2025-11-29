# pycycle-mcp

A lightweight MCP-style server that exposes pyCycle/OpenMDAO engine cycle models as JSON-schema tools via FastMCP. The server maintains an in-memory mapping of `session_id` to OpenMDAO `Problem` instances so multiple cycles can be configured and evaluated in one process.

## Features

- Create, configure, and close pyCycle engine cycle models (turbofan, turbojet, turboshaft, or custom).
- List inputs/outputs, set inputs, and fetch outputs with structured JSON results.
- Execute models, run parametric sweeps, and compute total derivatives via OpenMDAO.
- FastMCP-based server with explicit JSON Schemas for each tool, plus a lightweight `ping` tool that works without pyCycle/OpenMDAO installed.
- Console script `pycycle-mcp-server` that mirrors the tigl-mcp/su2-mcp CLI shape (stdio or HTTP transports).

## Installation

The package ships with optional extras for full pyCycle support and development tooling.

```bash
python -m pip install .[full]   # installs openmdao + pycycle
python -m pip install .[dev]    # installs lint/test dependencies
```

## Usage

Run the server over stdio (default):

```bash
pycycle-mcp-server --transport stdio
```

Expose the server over HTTP/streamable-http (the CLI normalizes `--transport http` to `streamable-http` for compatibility):

```bash
pycycle-mcp-server --transport http --host 0.0.0.0 --port 8000 --path /mcp
```

Call the lightweight ping tool through any MCP client to verify the server is healthy even when pyCycle/OpenMDAO are missing.

The tool functions are pure Python callables and can be imported directly for use inside a larger MCP host. A convenience `build_server` factory is available via `pycycle_mcp_server.fastmcp_server.build_server`, and `python -m pycycle_mcp_server --serve ...` remains supported for legacy workflows.

## Development

We recommend enabling pre-commit hooks for formatting and linting:

```bash
python -m pip install pre-commit
pre-commit install
```

Run quality checks locally:

```bash
python -m pip install .[dev,full]
ruff check .
black --check .
mypy .
pytest
```

The repository uses a FastMCP-powered helper CLI rather than a bespoke host. Integrators can reuse the FastMCP server or wrap the tool functions in their preferred transport.
