"""Shared-CPACS adapter for the pyCycle MCP.

Reads engine parameters from ``//vehicles/engines`` in the CPACS XML,
calls the actual pyCycle MCP tools (create_cycle_model → set_inputs →
run_cycle) to compute engine performance, and writes results back.

When OpenMDAO/pyCycle is not installed, reports the failure clearly.
"""

from __future__ import annotations

import logging
from typing import Any
from xml.etree import ElementTree as ET

LOGGER = logging.getLogger(__name__)


def _check_pycycle_available() -> bool:
    """Check if pyCycle and OpenMDAO are importable."""
    try:
        import openmdao.api  # noqa: F401
        import pycycle.api  # noqa: F401

        return True
    except ImportError:
        return False


def read_from_cpacs(
    cpacs_xml: str,
    flight_conditions: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Extract engine parameters from the CPACS XML."""
    root = ET.fromstring(cpacs_xml)

    engine_el = root.find(".//vehicles/engines/engine")
    engine_name = "unknown"
    engine_uid = None
    thrust00 = None
    bpr00 = None
    opr00 = None

    if engine_el is not None:
        engine_uid = engine_el.get("uID")
        name_el = engine_el.find("name")
        if name_el is not None and name_el.text:
            engine_name = name_el.text
        t_el = engine_el.find(".//analysis/thrust00")
        if t_el is not None and t_el.text:
            thrust00 = float(t_el.text)
        b_el = engine_el.find(".//analysis/BPR00")
        if b_el is not None and b_el.text:
            bpr00 = float(b_el.text)
        o_el = engine_el.find(".//analysis/OPR00")
        if o_el is not None and o_el.text:
            opr00 = float(o_el.text)

    aero_el = root.find(".//vehicles/aircraft/model/analysisResults/aero/coefficients")
    cd_from_aero = None
    if aero_el is not None:
        cd_el = aero_el.find("CD")
        if cd_el is not None and cd_el.text:
            cd_from_aero = float(cd_el.text)

    # No default. 122.4 m2 is the D150's wing area, and defaulting to it meant
    # any file without a reference area was sized as if it were a D150.
    ref_area_el = root.find(".//vehicles/aircraft/model/reference/area")
    ref_area = float(ref_area_el.text) if ref_area_el is not None and ref_area_el.text else None

    fc = flight_conditions or {}

    return {
        "engine_uid": engine_uid,
        "engine_name": engine_name,
        "thrust00_N": thrust00,
        "bpr00": bpr00,
        "opr00": opr00,
        "cd_from_aero": cd_from_aero,
        "ref_area_m2": ref_area,
        "mach": fc.get("mach", 0.78),
        "altitude_ft": fc.get("altitude_ft", 35000.0),
    }


def _compute_thrust_required(cd: float, mach: float, altitude_ft: float, ref_area_m2: float) -> float:
    """Estimate thrust required [lbf] from drag coefficient."""
    import math

    alt_m = altitude_ft * 0.3048
    T0, P0 = 288.15, 101325.0
    if alt_m <= 11000:
        T = T0 - 0.0065 * alt_m
        P = P0 * (T / T0) ** 5.2561
    else:
        T = 216.65
        P = 22632.1 * math.exp(-0.00015769 * (alt_m - 11000))
    q = 0.5 * 1.4 * P * mach**2
    drag_N = cd * q * ref_area_m2
    return drag_N * 0.224809


def _run_real_pycycle(inputs: dict[str, Any]) -> dict[str, Any]:
    """Run actual pyCycle/OpenMDAO through the real MCP tool functions."""
    from pycycle_mcp.tools.create_model import close_cycle_model, create_cycle_model
    from pycycle_mcp.tools.execution import run_cycle
    from pycycle_mcp.tools.variables import set_inputs

    # Create a turbofan model
    create_result = create_cycle_model(
        {
            "cycle_type": "turbofan",
            "mode": "design",
            "options": {},
        }
    )

    if "error" in create_result:
        return {"error": create_result["error"], "solver": "pycycle_openmdao"}

    session_id = str(create_result["session_id"])

    try:
        # Build input values from CPACS data
        input_values: dict[str, Any] = {
            "fc.MN": inputs["mach"],
            "fc.alt": inputs["altitude_ft"],
        }

        # Explicit design-thrust override takes priority (used by the
        # engine-resizing / cruise-match skills to drive the cycle to a
        # specific sizing point).  Falls back to the aero-drag estimate, then
        # the CPACS thrust00 value, then a default.
        if inputs.get("design_thrust_lbf") is not None:
            input_values["Fn_DES"] = float(inputs["design_thrust_lbf"])
        elif inputs.get("cd_from_aero") is not None:
            cd_in = float(inputs["cd_from_aero"])
            if cd_in <= 0.0 or cd_in > 20.0:
                # Sizing an engine to an impossible drag is how a single bad
                # aero result became a -29 GN engine and a negative fuel burn.
                return {
                    "error": {
                        "type": "unphysical_input",
                        "message": (f"Refusing to size an engine from a drag coefficient of {cd_in:.6g}."),
                        "details": (
                            "Drag coefficients are positive and of order 0.01 "
                            "to 1 for this class of aircraft. Re-run the aero "
                            "stage and check its result before sizing an engine."
                        ),
                    },
                    "solver": "pycycle_openmdao",
                }
            if inputs.get("ref_area_m2") is None:
                # Drag is CD * q * S, so without S there is no thrust to size
                # to. This used to default to the D150's 122.4 m2, which sized
                # every aircraft as if it had a narrow-body wing.
                return {
                    "error": {
                        "type": "missing_input",
                        "message": ("Cannot convert drag to thrust: the CPACS file states no reference area."),
                        "details": (
                            "Add //vehicles/aircraft/model/reference/area. It "
                            "is not defaulted, because substituting one "
                            "aircraft's wing area for another's silently "
                            "produces a plausible and wrong engine size."
                        ),
                    },
                    "solver": "pycycle_openmdao",
                }
            thrust_lbf = _compute_thrust_required(
                inputs["cd_from_aero"],
                inputs["mach"],
                inputs["altitude_ft"],
                inputs["ref_area_m2"],
            )
            input_values["Fn_DES"] = thrust_lbf
        elif inputs.get("thrust00_N"):
            input_values["Fn_DES"] = inputs["thrust00_N"] * 0.224809 * 0.3
        else:
            # Nothing to size the engine from: no explicit design thrust, no
            # drag from a preceding aero run, and no engine defined in the
            # CPACS file. This previously substituted Fn_DES = 5900 lbf, a
            # number with no provenance that silently became "the engine".
            return {
                "error": {
                    "type": "missing_engine_definition",
                    "message": (
                        "Cannot size the engine: the CPACS file defines no "
                        "engine, and no design thrust or drag coefficient was "
                        "supplied."
                    ),
                    "details": (
                        "Do one of: add an <engines> block to the CPACS file; "
                        "pass design_thrust_lbf explicitly, as the engine-resize "
                        "and cruise-match skills do; or run the aero stage first "
                        "so the engine can be sized to the computed drag."
                    ),
                },
                "solver": "pycycle_openmdao",
            }

        set_inputs(
            {
                "session_id": session_id,
                "values": input_values,
                "allow_missing": True,
            }
        )

        # Run the cycle
        outputs_of_interest = [
            "perf.Fn",
            "perf.TSFC",
            "perf.OPR",
            "perf.Fg",
            "splitter.BPR",
            "fc.Fl_O:stat:MN",
            "fc.alt",
            "inlet.F_ram",
            "burner.Wfuel",
        ]

        run_result = run_cycle(
            {
                "session_id": session_id,
                "outputs_of_interest": outputs_of_interest,
            }
        )

        if not run_result.get("success"):
            return {
                "error": {
                    "type": "solver_failure",
                    "message": "pyCycle model did not converge",
                    "details": run_result.get("messages", []),
                },
                "solver": "pycycle_openmdao",
            }

        outputs = run_result.get("outputs", {})

        fn = outputs.get("perf.Fn", 0.0) or 0.0
        tsfc = outputs.get("perf.TSFC", 0.0) or 0.0
        opr = outputs.get("perf.OPR", 0.0) or 0.0
        fg = outputs.get("perf.Fg", 0.0) or 0.0
        bpr = outputs.get("splitter.BPR", 0.0) or 0.0
        wfuel = outputs.get("burner.Wfuel", 0.0) or 0.0

        # OpenMDAO reporting success is not the same as the cycle being
        # physical. A converged solve returned Fn = -29 GN with a negative
        # burner fuel flow on a partner's machine, and every downstream tool
        # accepted it. Check the signs before publishing anything.
        for label, value, unit in (
            ("net thrust", fn, "lbf"),
            ("gross thrust", fg, "lbf"),
            ("fuel flow", wfuel, "lbm/s"),
            ("TSFC", tsfc, "lb/(lbf.hr)"),
            ("overall pressure ratio", opr, ""),
        ):
            if value is not None and float(value) < 0.0:
                return {
                    "error": {
                        "type": "unphysical_result",
                        "message": (f"pyCycle converged but returned a negative {label} ({float(value):.6g} {unit})."),
                        "details": (
                            "A negative value here means the cycle solved to a "
                            "non-physical operating point, usually because the "
                            "requested design thrust was itself invalid. The "
                            "result was not written to CPACS. Check the design "
                            "thrust and the drag it was derived from."
                        ),
                    },
                    "solver": "pycycle_openmdao",
                }

        return {
            "engine_uid": inputs.get("engine_uid"),
            "engine_name": inputs.get("engine_name", "unknown"),
            "Fn_DES_lbf": round(float(input_values["Fn_DES"]), 2),
            "Fn_N": round(float(fn) * 4.44822, 2),
            "Fn_lbf": round(float(fn), 2),
            "Fg_N": round(float(fg) * 4.44822, 2),
            "TSFC_lb_lbf_hr": round(float(tsfc), 5),
            # Mass-based TSFC in kg/(N*s), the unit NSEG's segment physics
            # consumes: lbm/(lbf*hr) * (0.453592 kg/lbm) / (4.44822 N/lbf) / 3600 s.
            # (A bare /3600 would silently drop the 1/g0 between lbm and lbf.)
            "TSFC_1_per_s": round(float(tsfc) * 0.453592 / 4.44822 / 3600.0, 10),
            "OPR": round(float(opr), 2),
            "BPR": round(float(bpr), 2),
            "fuel_flow_kg_s": round(float(wfuel) * 0.453592, 6),
            "solver": "pycycle_openmdao",
            "mach": inputs["mach"],
            "altitude_ft": inputs["altitude_ft"],
            "all_outputs": {k: v for k, v in outputs.items() if v is not None},
        }

    finally:
        close_cycle_model({"session_id": session_id})


def write_to_cpacs(cpacs_xml: str, results: dict[str, Any]) -> str:
    """Write cycle results into ``//vehicles/engines/engine/analysis/mcpResults``."""
    root = ET.fromstring(cpacs_xml)

    engine_el = root.find(".//vehicles/engines/engine")
    if engine_el is None:
        engines = _ensure_path(root, "vehicles/engines")
        engine_el = ET.SubElement(engines, "engine")
        engine_el.set("uID", results.get("engine_uid") or "engine_mcp")

    analysis = engine_el.find("analysis")
    if analysis is None:
        analysis = ET.SubElement(engine_el, "analysis")

    existing = analysis.find("mcpResults")
    if existing is not None:
        analysis.remove(existing)

    mcp_el = ET.SubElement(analysis, "mcpResults")
    ET.SubElement(mcp_el, "solver").text = results.get("solver", "unknown")

    if results.get("error"):
        err_el = ET.SubElement(mcp_el, "error")
        err_info = results["error"]
        if isinstance(err_info, dict):
            ET.SubElement(err_el, "type").text = str(err_info.get("type", "unknown"))
            ET.SubElement(err_el, "message").text = str(err_info.get("message", ""))
        else:
            ET.SubElement(err_el, "message").text = str(err_info)
    else:
        ET.SubElement(mcp_el, "mach").text = str(results.get("mach", 0.0))
        ET.SubElement(mcp_el, "altitudeFt").text = str(results.get("altitude_ft", 0.0))
        ET.SubElement(mcp_el, "Fn_N").text = str(results.get("Fn_N", 0.0))
        ET.SubElement(mcp_el, "Fn_lbf").text = str(results.get("Fn_lbf", 0.0))
        ET.SubElement(mcp_el, "Fg_N").text = str(results.get("Fg_N", 0.0))
        ET.SubElement(mcp_el, "TSFC_lb_lbf_hr").text = str(results.get("TSFC_lb_lbf_hr", 0.0))
        ET.SubElement(mcp_el, "TSFC_1_per_s").text = str(results.get("TSFC_1_per_s", 0.0))
        ET.SubElement(mcp_el, "OPR").text = str(results.get("OPR", 0.0))
        ET.SubElement(mcp_el, "BPR").text = str(results.get("BPR", 0.0))
        ET.SubElement(mcp_el, "fuelFlow_kg_s").text = str(results.get("fuel_flow_kg_s", 0.0))

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def run_adapter(
    cpacs_xml: str,
    flight_conditions: dict[str, float] | None = None,
    design_thrust_lbf: float | None = None,
) -> tuple[str, dict[str, Any]]:
    """Full read→process→write cycle for the pyCycle domain.

    Calls real pyCycle/OpenMDAO when available; reports the error
    honestly when it's not.

    Parameters
    ----------
    design_thrust_lbf : float, optional
        Explicit design net thrust ``Fn_DES`` [lbf] to size the cycle to.
        When supplied it overrides the aero-drag-derived estimate.  Used by
        the engine-resizing and cruise-match skills to iterate on engine size.
    """
    inputs = read_from_cpacs(cpacs_xml, flight_conditions)
    if design_thrust_lbf is not None:
        inputs["design_thrust_lbf"] = float(design_thrust_lbf)

    if not _check_pycycle_available():
        results = {
            "error": {
                "type": "missing_dependency",
                "message": (
                    "OpenMDAO/pyCycle not installed. "
                    "Install with: pip install openmdao om-pycycle. "
                    "No engine performance computed."
                ),
            },
            "solver": "pycycle_openmdao",
            "engine_uid": inputs.get("engine_uid"),
            "engine_name": inputs.get("engine_name"),
            "mach": inputs["mach"],
            "altitude_ft": inputs["altitude_ft"],
        }
    else:
        results = _run_real_pycycle(inputs)

    updated_xml = write_to_cpacs(cpacs_xml, results)
    return updated_xml, results


def _ensure_path(root: ET.Element, path: str) -> ET.Element:
    current = root
    for part in path.split("/"):
        child = current.find(part)
        if child is None:
            child = ET.SubElement(current, part)
        current = child
    return current
