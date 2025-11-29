"""Execution tools for running cycle models."""

from __future__ import annotations

import logging

from ..errors import error_response, to_error
from ..session_manager import session_manager
from ..utils import error_on_missing_session

LOGGER = logging.getLogger(__name__)

DEFAULT_OUTPUTS = [
    "Fn",  # net thrust
    "Fnet",
    "TSFC",
    "eff",
    "power",
]


def run_cycle(payload: dict[str, object]) -> dict[str, object]:
    """Run the cycle model and return selected outputs."""

    session_id = payload.get("session_id")
    outputs_of_interest: list[str] = payload.get("outputs_of_interest") or DEFAULT_OUTPUTS  # type: ignore[assignment]
    use_driver = bool(payload.get("use_driver", False))

    if not session_id:
        return error_response("ValidationError", "session_id is required")

    try:
        problem, _ = session_manager.get(str(session_id))
        messages: list[str] = []
        try:
            if use_driver:
                messages.append("Ran driver")
                problem.run_driver()
            else:
                messages.append("Ran model")
                problem.run_model()
        except Exception as exc:
            LOGGER.error("Run failed: %s", exc)
            return to_error(exc)

        outputs: dict[str, object | None] = {}
        for name in outputs_of_interest:
            try:
                outputs[name] = problem.get_val(name)
            except Exception as exc:
                outputs[name] = None
                messages.append(f"Missing output {name}: {exc}")
        converged = getattr(
            getattr(problem, "_metadata", None), "get", lambda *_: None
        )("converged", None)

        return {
            "success": True,
            "converged": converged,
            "iterations": getattr(problem, "iter_count", None),
            "outputs": outputs,
            "residual_norm": getattr(problem, "_residual_norm", None),
            "messages": messages,
        }
    except KeyError as exc:
        return error_on_missing_session(str(session_id), exc)
    except Exception as exc:  # pragma: no cover
        return to_error(exc)
