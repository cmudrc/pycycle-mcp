"""The engine is not sized to a drag that SU2 computed at another Mach number."""

from __future__ import annotations

from pycycle_mcp.cpacs_adapter import _aero_mach_mismatch, read_from_cpacs


def _cpacs(aero_mach: str | None) -> str:
    mach = f"<mach>{aero_mach}</mach>" if aero_mach is not None else ""
    return (
        "<cpacs><vehicles><aircraft><model uID='m'>"
        "<reference><area>122.4</area></reference>"
        f"<analysisResults><aero>{mach}<coefficients><CD>0.021</CD></coefficients></aero>"
        "</analysisResults></model></aircraft></vehicles></cpacs>"
    )


def test_drag_from_another_mach_is_refused() -> None:
    inputs = read_from_cpacs(_cpacs("0.7"), {"mach": 0.78, "altitude_ft": 35000.0})
    assert inputs["cd_aero_mach"] == 0.7
    err = _aero_mach_mismatch(inputs)
    assert err is not None
    assert err["error"]["type"] == "inconsistent_inputs"
    assert "Mach 0.78" in err["error"]["message"] and "Mach 0.7." in err["error"]["message"]


def test_matching_mach_or_unrecorded_mach_is_not_refused() -> None:
    assert _aero_mach_mismatch(read_from_cpacs(_cpacs("0.78"), {"mach": 0.78})) is None
    assert _aero_mach_mismatch(read_from_cpacs(_cpacs(None), {"mach": 0.78})) is None


def test_explicit_design_thrust_is_not_checked() -> None:
    inputs = read_from_cpacs(_cpacs("0.7"), {"mach": 0.78})
    inputs["design_thrust_lbf"] = 6000.0
    assert _aero_mach_mismatch(inputs) is None


def test_refusal_leaves_the_file_unchanged() -> None:
    from pycycle_mcp.cpacs_adapter import run_adapter

    xml = _cpacs("0.7")
    out_xml, res = run_adapter(xml, flight_conditions={"mach": 0.78, "altitude_ft": 35000.0})
    assert res["error"]["type"] == "inconsistent_inputs"
    assert out_xml == xml
