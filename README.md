# pycycle-mcp

A lightweight MCP-style server that exposes [NASA pyCycle](https://github.com/OpenMDAO/pyCycle)/OpenMDAO engine cycle models as JSON-schema tools via FastMCP. The server maintains an in-memory mapping of `session_id` to OpenMDAO `Problem` instances so multiple cycles can be configured and evaluated in one process.

## Features

- Create, configure, and close pyCycle engine cycle models (high-bypass turbofan, turbojet, or custom).
- Bundled cycle definitions from NASA's pyCycle `example_cycles` with sensible design-point defaults — models run out of the box.
- List inputs/outputs, set inputs, and fetch outputs with structured JSON results.
- Execute models, run parametric sweeps, and compute total derivatives via OpenMDAO.
- FastMCP-based server with explicit JSON Schemas for each tool, plus a lightweight `ping` tool that works without pyCycle/OpenMDAO installed.
- Console script `pycycle-mcp-server` that mirrors the tigl-mcp/su2-mcp CLI shape (stdio or HTTP transports).

## Installation

The package ships with optional extras for full pyCycle support and development tooling. The `[full]` extra installs [om-pycycle](https://github.com/OpenMDAO/pyCycle) directly from GitHub since the PyPI `pycycle` package is an unrelated project.

```bash
python -m pip install .[full]   # installs openmdao + NASA om-pycycle from GitHub
python -m pip install .[dev]    # installs lint/test dependencies
```

## Usage

Run the server over stdio (default):

```bash
pycycle-mcp-server --transport stdio
```

Expose the server over HTTP/streamable-http:

```bash
pycycle-mcp-server --transport http --host 0.0.0.0 --port 8001
```

### Quick example: create and run a turbofan

```python
# Using the MCP tools programmatically:
from pycycle_mcp_server.tools.create_model import create_cycle_model
from pycycle_mcp_server.tools.execution import run_cycle

result = create_cycle_model({
    "cycle_type": "turbofan",
    "mode": "design",
})
session_id = result["session_id"]

run_result = run_cycle({
    "session_id": session_id,
    "outputs_of_interest": ["perf.Fn", "perf.TSFC", "perf.OPR", "splitter.BPR"],
})
print(run_result["outputs"])
# {'perf.Fn': 5900.0, 'perf.TSFC': 0.889, 'perf.OPR': 30.55, 'splitter.BPR': 1.5}
```

### Supported cycle types

| `cycle_type` | Description | Key outputs |
|--------------|-------------|-------------|
| `turbofan`   | High-bypass 2-spool turbofan (HBTF) with fan, LPC, HPC, HPT, LPT, bypass | Fn, TSFC, OPR, BPR |
| `turbojet`   | Single-spool turbojet with compressor, combustor, turbine | Fn, TSFC, OPR |
| `custom`     | User-provided cycle class via `cycle_module_path` | Depends on model |

### Integration with TiGL and SU2

This server is designed to work alongside [tigl-mcp](https://github.com/cmudrc/tigl-mcp) and [su2-mcp](https://github.com/cmudrc/su2-mcp) in an automated aircraft analysis pipeline:

1. **TiGL MCP** (port 8000): CPACS → STEP geometry
2. **SU2 MCP** (port 8002): STEP → volume mesh → Euler CFD → CL/CD
3. **pyCycle MCP** (port 8001): Flight conditions + drag → engine sizing (thrust, TSFC, fuel flow)

The key data handoff: SU2's drag coefficient is converted to a thrust requirement (`Fn_DES = CD × q∞ × S_ref`) which sizes the engine to overcome aircraft drag at cruise.

#### Config-driven pipeline

The orchestration script (`pipeline/tigl_to_su2.py`) accepts a `pipeline_config.yaml` that controls all pipeline parameters including engine settings:

```yaml
engine:
  type: turbofan           # turbofan | turbojet
  default_thrust_lbf: 5900.0
  # Uncomment to override NASA HBTF defaults:
  # turbofan:
  #   fan_pr: 1.685
  #   hpc_pr: 9.369
  #   t4_max_R: 2857.0
```

Engine design parameters that can be set via config or `set_inputs` MCP tool: `fan.PR`, `fan.eff`, `lpc.PR/eff`, `hpc.PR/eff`, `hpt.eff`, `lpt.eff`, `T4_MAX`, `Fn_DES`.

Hardcoded internals (in the HBTF cycle definition): duct pressure losses, bleed fractions, nozzle velocity coefficients, shaft power extractions, Newton solver tolerances.

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
