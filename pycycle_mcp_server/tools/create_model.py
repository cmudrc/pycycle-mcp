"""Tools for creating and summarizing pyCycle/OpenMDAO models."""

from __future__ import annotations

import logging
from collections.abc import Callable

from ..errors import error_response, to_error
from ..session_manager import session_manager
from ..types import CycleProblem
from ..utils import (
    error_on_missing_session,
    load_callable,
    select_interesting_variables,
)

LOGGER = logging.getLogger(__name__)

INTERESTING_INPUT_KEYWORDS = ["mach", "alt", "pr", "turbine", "throttle"]
INTERESTING_OUTPUT_KEYWORDS = ["fn", "fnet", "thrust", "tsfc", "power", "eff"]


CycleBuilder = Callable[[], object]


def _resolve_builtin_cycle(cycle_type: str) -> tuple[str, CycleBuilder]:
    """Resolve a built-in cycle type to a callable builder."""

    try:
        import pycycle.api as pyc_api
    except Exception as exc:  # pragma: no cover - exercised via tests
        raise ImportError("pycycle is required for built-in cycle types") from exc

    mapping: dict[str, CycleBuilder] = {
        "turbofan": pyc_api.Turbofan,
        "turbojet": pyc_api.Turbojet,
        "turboshaft": pyc_api.Turboshaft,
    }
    builder = mapping.get(cycle_type)
    if builder is None:
        raise ValueError(f"Unsupported cycle type: {cycle_type}")
    return builder.__name__, builder


def _build_problem(
    builder: CycleBuilder, mode: str, options: dict[str, object]
) -> tuple[CycleProblem, str]:
    try:
        from openmdao.api import Problem
    except Exception as exc:  # pragma: no cover - import failure path
        raise ImportError("openmdao is required to build cycle models") from exc

    problem: CycleProblem = Problem()
    model = builder()
    problem.model = model  # type: ignore[assignment]

    if hasattr(model, "set_default_mode"):
        try:
            model.set_default_mode(mode)
        except Exception as exc:  # pragma: no cover - depends on pycycle implementation
            LOGGER.debug("Failed to apply mode defaults: %s", exc)
    for key, value in options.items():
        if hasattr(model, "set_input_defaults"):
            try:
                model.set_input_defaults(key, value)
            except Exception:
                problem.set_val(key, value)
        else:
            problem.set_val(key, value)

    problem.setup()
    return problem, getattr(
        model,
        "name",
        builder.__name__ if hasattr(builder, "__name__") else str(builder),
    )


def _extract_variables(
    problem: CycleProblem, target: str
) -> list[tuple[str, dict[str, object]]]:
    if target == "inputs":
        items = problem.model.list_inputs(prom_name=True, out_stream=None)
    else:
        items = problem.model.list_outputs(prom_name=True, out_stream=None)
    return [(name, meta) for name, meta in items]


def _summarize_variables(
    problem: CycleProblem,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    inputs = _extract_variables(problem, "inputs")
    outputs = _extract_variables(problem, "outputs")

    interesting_inputs = select_interesting_variables(
        inputs, INTERESTING_INPUT_KEYWORDS
    )
    interesting_outputs = select_interesting_variables(
        outputs, INTERESTING_OUTPUT_KEYWORDS
    )

    def _render(
        names: list[str], source: list[tuple[str, dict[str, object]]]
    ) -> list[dict[str, object]]:
        rendered: list[dict[str, object]] = []
        metadata_map = {name: meta for name, meta in source}
        for name in names:
            meta = metadata_map.get(name, {})
            rendered.append(
                {"name": name, "units": meta.get("units"), "desc": meta.get("desc")}
            )
        return rendered

    return _render(interesting_inputs, inputs), _render(interesting_outputs, outputs)


def create_cycle_model(payload: dict[str, object]) -> dict[str, object]:
    """Instantiate a pyCycle/OpenMDAO Problem for a specified engine cycle."""

    cycle_type = payload.get("cycle_type")
    mode = payload.get("mode")
    options: dict[str, object] = payload.get("options", {})  # type: ignore[assignment]
    cycle_module_path = payload.get("cycle_module_path")

    if not cycle_type or not mode:
        return error_response("ValidationError", "cycle_type and mode are required")

    try:
        if cycle_type == "custom":
            if not cycle_module_path:
                raise ValueError("cycle_module_path is required for custom cycles")
            builder = load_callable(str(cycle_module_path))
            model_name = getattr(builder, "__name__", cycle_module_path)
        else:
            model_name, builder = _resolve_builtin_cycle(str(cycle_type))

        problem, resolved_name = _build_problem(
            builder=builder, mode=str(mode), options=options
        )
        session_id = session_manager.create_session(
            problem=problem, meta={"mode": mode, "options": options}
        )
        top_inputs, top_outputs = _summarize_variables(problem)

        return {
            "session_id": session_id,
            "model_name": resolved_name or model_name,
            "top_promoted_inputs": top_inputs,
            "top_promoted_outputs": top_outputs,
        }
    except Exception as exc:  # pragma: no cover - handled in tests via fake errors
        LOGGER.error("Failed to create cycle model: %s", exc)
        return to_error(exc)


def close_cycle_model(payload: dict[str, object]) -> dict[str, object]:
    """Close a pyCycle session and free resources."""

    session_id = payload.get("session_id")
    if not session_id:
        return error_response("ValidationError", "session_id is required")

    try:
        session_manager.close(str(session_id))
        return {"success": True}
    except Exception as exc:  # pragma: no cover
        return to_error(exc)


def get_cycle_summary(payload: dict[str, object]) -> dict[str, object]:
    """Return a succinct summary of the current cycle model."""

    session_id = payload.get("session_id")
    if not session_id:
        return error_response("ValidationError", "session_id is required")

    try:
        problem, meta = session_manager.get(str(session_id))
        mode = meta.get("mode")
        options = meta.get("options", {})
        inputs = _extract_variables(problem, "inputs")
        outputs = _extract_variables(problem, "outputs")

        def _populate(
            entries: list[tuple[str, dict[str, object]]],
        ) -> list[dict[str, object]]:
            rendered: list[dict[str, object]] = []
            for name, meta_entry in entries:
                rendered.append(
                    {
                        "name": name,
                        "units": meta_entry.get("units"),
                        "desc": meta_entry.get("desc"),
                        "current_value": meta_entry.get("val")
                        or meta_entry.get("value"),
                    }
                )
            return rendered

        return {
            "model_name": getattr(problem.model, "name", "cycle"),
            "mode": mode,
            "options": options,
            "key_inputs": _populate(inputs),
            "key_outputs": _populate(outputs),
        }
    except KeyError as exc:
        return error_on_missing_session(str(session_id), exc)
    except Exception as exc:  # pragma: no cover
        return to_error(exc)
