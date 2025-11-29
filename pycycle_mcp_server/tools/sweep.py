"""Sweep tools for parametric analyses."""

from __future__ import annotations

from ..errors import error_response, to_error
from ..session_manager import session_manager
from ..utils import error_on_missing_session, ordered_cartesian_product
from .execution import run_cycle


def sweep_inputs(payload: dict[str, object]) -> dict[str, object]:
    """Perform a parametric sweep over input variables."""

    session_id = payload.get("session_id")
    sweep_spec_raw = payload.get("sweep") or []
    sweep_spec = sweep_spec_raw if isinstance(sweep_spec_raw, list) else []
    outputs_raw = payload.get("outputs_of_interest") or []
    outputs_of_interest: list[str] = (
        outputs_raw if isinstance(outputs_raw, list) else []
    )
    use_driver = bool(payload.get("use_driver", False))
    skip_on_failure = bool(payload.get("skip_on_failure", True))

    if not session_id:
        return error_response("ValidationError", "session_id is required")
    if not sweep_spec:
        return error_response(
            "ValidationError", "sweep must include at least one variable"
        )

    try:
        problem, _ = session_manager.get(str(session_id))
        variables = [
            entry.get("name") for entry in sweep_spec if isinstance(entry, dict)
        ]
        value_sets = [
            entry.get("values", []) if isinstance(entry.get("values"), list) else []
            for entry in sweep_spec
            if isinstance(entry, dict)
        ]

        results: list[dict[str, object]] = []
        for value_combo in ordered_cartesian_product(value_sets):
            input_values = {
                name: value
                for name, value in zip(variables, value_combo, strict=False)
                if isinstance(name, str)
            }
            try:
                for var_name, var_value in input_values.items():
                    problem.set_val(var_name, var_value)
                run_result = run_cycle(
                    {
                        "session_id": session_id,
                        "outputs_of_interest": outputs_of_interest,
                        "use_driver": use_driver,
                    }
                )
                success = not run_result.get("error") and bool(
                    run_result.get("success")
                )
                results.append(
                    {
                        "inputs": input_values,
                        "success": success,
                        "outputs": run_result.get("outputs", {}),
                        "error_message": (
                            None if success else str(run_result.get("error"))
                        ),
                    }
                )
            except Exception as exc:
                if skip_on_failure:
                    results.append(
                        {
                            "inputs": input_values,
                            "success": False,
                            "outputs": {},
                            "error_message": str(exc),
                        }
                    )
                    continue
                return to_error(exc)

        return {"results": results}
    except KeyError as exc:
        return error_on_missing_session(str(session_id), exc)
    except Exception as exc:  # pragma: no cover
        return to_error(exc)
