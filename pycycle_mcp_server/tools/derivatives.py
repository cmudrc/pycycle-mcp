"""Derivative computation tools."""

from __future__ import annotations

from typing import cast

from ..errors import error_response, to_error
from ..session_manager import session_manager
from ..utils import error_on_missing_session


def _format_by_pair(jacobian: dict[tuple[str, str], object]) -> dict[str, dict[str, object]]:
    formatted: dict[str, dict[str, object]] = {}
    for (of, wrt), value in jacobian.items():
        formatted.setdefault(of, {})[wrt] = (
            value.tolist() if hasattr(value, "tolist") else value
        )
    return formatted


def compute_totals(payload: dict[str, object]) -> dict[str, object]:
    """Compute total derivatives using OpenMDAO."""

    session_id = payload.get("session_id")
    of: list[str] = payload.get("of", [])  # type: ignore[assignment]
    wrt: list[str] = payload.get("wrt", [])  # type: ignore[assignment]
    return_format = payload.get("return_format", "by_pair")

    if not session_id:
        return error_response("ValidationError", "session_id is required")
    if not of or not wrt:
        return error_response("ValidationError", "of and wrt must be provided")

    try:
        problem, _ = session_manager.get(str(session_id))
        totals = problem.compute_totals(of=of, wrt=wrt)

        if return_format == "dense":
            data = []
            for output_name in of:
                row = []
                for input_name in wrt:
                    cell = totals[(output_name, input_name)]
                    row.append(cell.tolist() if hasattr(cell, "tolist") else cell)
                data.append(row)
            jacobian: dict[str, object] = {"of": of, "wrt": wrt, "data": data}
        else:
            jacobian = cast(dict[str, object], _format_by_pair(totals))

        return {"jacobian": jacobian, "messages": ["Totals computed"]}
    except KeyError as exc:
        return error_on_missing_session(str(session_id), exc)
    except Exception as exc:  # pragma: no cover
        return to_error(exc)
