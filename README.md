# pycycle-mcp

A lightweight MCP-style server that exposes pyCycle/OpenMDAO engine cycle models as JSON-schema tools. The server maintains an in-memory mapping of `session_id` to OpenMDAO `Problem` instances so multiple cycles can be configured and evaluated in one process.

## Features

- Create, configure, and close pyCycle engine cycle models (turbofan, turbojet, turboshaft, or custom).
- List inputs/outputs, set inputs, and fetch outputs with structured JSON results.
- Execute models, run parametric sweeps, and compute total derivatives via OpenMDAO.
- Minimal CLI for invoking tools locally: `python -m pycycle_mcp_server --tool ... --payload ...`.

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

The tool functions are pure Python callables and can be imported directly for use inside a larger MCP host.

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

The repository uses a small helper CLI rather than a full MCP host. Integrators can wrap the tool functions in their preferred transport.
