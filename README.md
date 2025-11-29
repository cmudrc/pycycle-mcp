# pycycle-mcp

A lightweight MCP-style server that exposes pyCycle/OpenMDAO engine cycle models as JSON-schema tools via FastMCP. The server maintains an in-memory mapping of `session_id` to OpenMDAO `Problem` instances so multiple cycles can be configured and evaluated in one process.

## Features

- Create, configure, and close pyCycle engine cycle models (turbofan, turbojet, turboshaft, or custom).
- List inputs/outputs, set inputs, and fetch outputs with structured JSON results.
- Execute models, run parametric sweeps, and compute total derivatives via OpenMDAO.
- FastMCP-based server with explicit JSON Schemas for each tool.
- Minimal CLI for invoking tools locally or running the FastMCP server: `python -m pycycle_mcp_server --tool ... --payload ...` or `python -m pycycle_mcp_server --serve`.

## Installation

The package ships with optional extras for full pyCycle support and development tooling.

```bash
python -m pip install .[full]   # installs openmdao + pycycle
python -m pip install .[dev]    # installs lint/test dependencies
```

## Usage

Create a turbofan session in design mode:

```bash
python -m pycycle_mcp_server \
  --tool create_cycle_model \
  --payload '{"cycle_type":"turbofan","mode":"design"}'
```

List variables from an existing session:

```bash
python -m pycycle_mcp_server \
  --tool list_variables \
  --payload '{"session_id":"<session>","kind":"inputs"}'
```

Run the model and retrieve key outputs:

```bash
python -m pycycle_mcp_server \
  --tool run_cycle \
  --payload '{"session_id":"<session>","outputs_of_interest":["Fn","TSFC"]}'
```

Run the FastMCP server over stdio (default) or HTTP transports:

```bash
python -m pycycle_mcp_server --serve --transport streamable-http --host 0.0.0.0 --port 8000
```

The tool functions are pure Python callables and can be imported directly for use inside a larger MCP host. A convenience `build_server` factory is available via `pycycle_mcp_server.fastmcp_server.build_server`.

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
