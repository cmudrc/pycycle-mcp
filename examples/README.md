# Examples

These examples exercise the current deterministic implementation surface.
They are designed to run from the repository root with `PYTHONPATH=src`.

- `client/tool_discovery.py`: list registered MCP tools via the in-process FastMCP app.
- `cpacs/session_lifecycle.py`: create a deterministic pyCycle-style session, summarize it, and close it.
- `cpacs/export_snapshot.py`: run deterministic output and derivative snapshot logic from a sample session.
- `server/http_launch_config.py`: show the non-blocking HTTP transport configuration shape.
