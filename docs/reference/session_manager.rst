Session Management
==================

``SessionManager`` stores in-memory cycle problem objects and maps them to
UUID-based session identifiers.

Current guarantees
------------------

- Session creation returns an opaque UUID string.
- Missing sessions raise a ``KeyError`` and are surfaced as structured MCP
  errors by tool wrappers.
- Closing a session removes the stored problem from memory.

.. automodule:: pycycle_mcp.session_manager
   :members:
