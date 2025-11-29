"""Session management for pyCycle MCP server."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from .types import CycleProblem


@dataclass
class SessionRecord:
    """Container for an OpenMDAO Problem and metadata."""

    problem: CycleProblem
    meta: dict[str, object] = field(default_factory=dict)


class SessionManager:
    """Manage pyCycle/OpenMDAO Problem sessions keyed by UUID."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}

    def create_session(
        self, problem: CycleProblem, meta: dict[str, object] | None = None
    ) -> str:
        """Register a new session and return its identifier."""

        session_id = str(uuid.uuid4())
        self._sessions[session_id] = SessionRecord(problem=problem, meta=meta or {})
        return session_id

    def get(self, session_id: str) -> tuple[CycleProblem, dict[str, object]]:
        """Retrieve the problem and metadata for a session."""

        record = self._sessions.get(session_id)
        if record is None:
            raise KeyError(f"Unknown session_id: {session_id}")
        return record.problem, record.meta

    def close(self, session_id: str) -> None:
        """Remove a session."""

        if session_id in self._sessions:
            del self._sessions[session_id]


session_manager = SessionManager()
"""Module-level session manager for convenience."""
