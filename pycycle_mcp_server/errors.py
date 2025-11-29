"""Error helpers for the pyCycle MCP server.

Provides a typed container for MCP errors and helper utilities to keep
responses consistent across tools.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MCPError:
    """Structured MCP error payload.

    Attributes:
        error_type: High-level error category.
        message: Human readable description of the error.
        details: Optional extra context.
    """

    error_type: str
    message: str
    details: object | None = None

    def to_response(self) -> dict[str, object]:
        """Convert the error to a response dictionary."""

        return {
            "error": {
                "type": self.error_type,
                "message": self.message,
                "details": self.details,
            }
        }


def error_response(
    error_type: str, message: str, details: object | None = None
) -> dict[str, object]:
    """Return a standardized MCP error response.

    Args:
        error_type: High-level error category.
        message: Human readable description.
        details: Optional extra context for debugging.

    Returns:
        A mapping that matches the MCP error envelope.
    """

    return MCPError(
        error_type=error_type, message=message, details=details
    ).to_response()


def to_error(err: Exception) -> dict[str, object]:
    """Convert an exception into an MCP error response."""

    return error_response(error_type=err.__class__.__name__, message=str(err))
