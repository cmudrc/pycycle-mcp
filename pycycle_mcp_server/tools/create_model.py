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
    """Resolve a built-in cycle type to a callable builder.

    NASA pyCycle provides engine components (Compressor, Turbine, etc.)
    rather than ready-made engine classes. We ship bundled cycle definitions
    that wire those components into complete engine models.
    """

    try:
        import pycycle.api as pyc_api  # noqa: F401 – verify pycycle is installed
    except Exception as exc:
        raise ImportError("pycycle (om-pycycle) is required for built-in cycle types") from exc

    from ..cycles.high_bypass_turbofan import HBTF
    from ..cycles.simple_turbojet import Turbojet

    mapping: dict[str, CycleBuilder] = {
        "turbofan": lambda: HBTF(thermo_method="CEA"),
        "turbojet": lambda: Turbojet(),
    }
    builder = mapping.get(cycle_type)
    if builder is None:
        supported = ", ".join(sorted(mapping.keys()))
        raise ValueError(f"Unsupported cycle type: {cycle_type}. Supported: {supported}")
    return cycle_type, builder


def _build_problem(
    builder: CycleBuilder, mode: str, options: dict[str, object]
) -> tuple[CycleProblem, str]:
    try:
        from openmdao.api import Problem
    except Exception as exc:
        raise ImportError("openmdao is required to build cycle models") from exc

    problem: CycleProblem = Problem()
    model = builder()
    problem.model = model  # type: ignore[assignment]

    problem.setup(check=False)

    # Apply default design-point values for built-in cycles
    _apply_design_defaults(problem, model, mode)

    for key, value in options.items():
        try:
            problem.set_val(key, value)
        except Exception as exc:
            LOGGER.debug("Could not set %s=%s: %s", key, value, exc)

    return problem, type(model).__name__


def _apply_design_defaults(
    problem: CycleProblem, model: object, mode: str
) -> None:
    """Set sensible design-point values so the model can run out of the box."""
    from ..cycles.high_bypass_turbofan import HBTF
    from ..cycles.simple_turbojet import Turbojet

    if isinstance(model, HBTF):
        problem.set_val("fan.PR", 1.685)
        problem.set_val("fan.eff", 0.8948)
        problem.set_val("lpc.PR", 1.935)
        problem.set_val("lpc.eff", 0.9243)
        problem.set_val("hpc.PR", 9.369)
        problem.set_val("hpc.eff", 0.8707)
        problem.set_val("hpt.eff", 0.8888)
        problem.set_val("lpt.eff", 0.8996)
        problem.set_val("fc.alt", 35000.0, units="ft")
        problem.set_val("fc.MN", 0.8)
        problem.set_val("T4_MAX", 2857.0, units="degR")
        problem.set_val("Fn_DES", 5900.0, units="lbf")
        # Initial guesses for Newton solver
        problem["balance.FAR"] = 0.025
        problem["balance.W"] = 100.0
        problem["balance.lpt_PR"] = 4.0
        problem["balance.hpt_PR"] = 3.0
        problem["fc.balance.Pt"] = 5.2
        problem["fc.balance.Tt"] = 440.0

    elif isinstance(model, Turbojet):
        problem.set_val("fc.alt", 0.0, units="ft")
        problem.set_val("fc.MN", 0.000001)
        problem.set_val("balance.Fn_target", 11800.0, units="lbf")
        problem.set_val("balance.T4_target", 2370.0, units="degR")
        problem.set_val("comp.PR", 13.5)
        problem.set_val("comp.eff", 0.83)
        problem.set_val("turb.eff", 0.86)
        problem["balance.FAR"] = 0.0175
        problem["balance.W"] = 168.0
        problem["balance.turb_PR"] = 4.46
        problem["fc.balance.Pt"] = 14.696
        problem["fc.balance.Tt"] = 518.67


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
