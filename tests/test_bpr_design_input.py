"""The bypass ratio must be a deliberate design input, not the element default.

Found 2026-09-10: the single-point HBTF build set fan/compressor pressure
ratios, T4 and design thrust, but never splitter.BPR. pyCycle's Splitter
element defaults it to 1.5, so every CPACS-driven run published a low-bypass
engine (BPR 1.5, TSFC ~0.89) as the aircraft's. The CPACS BPR00 the adapter
read was stored and ignored.
"""

from __future__ import annotations

import pytest


class _RecordingProblem:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    def set_val(self, name, value, units=None):  # noqa: ANN001
        self.values[name] = value

    def __setitem__(self, name, value):  # noqa: ANN001
        self.values[name] = value


def test_design_defaults_set_the_reference_bypass_ratio() -> None:
    pytest.importorskip("pycycle")
    from pycycle_mcp.cycles.high_bypass_turbofan import HBTF
    from pycycle_mcp.tools.create_model import _apply_design_defaults

    problem = _RecordingProblem()
    _apply_design_defaults(problem, HBTF(), "design")

    assert "splitter.BPR" in problem.values, "bypass ratio left at the element default"
    assert problem.values["splitter.BPR"] == pytest.approx(5.105)


def test_cpacs_bypass_ratio_is_read() -> None:
    from pycycle_mcp.cpacs_adapter import read_from_cpacs

    xml = (
        "<cpacs><vehicles>"
        "<engines><engine uID='e'><name>cfm</name>"
        "<analysis><BPR00>5.9</BPR00><OPR00>28.0</OPR00></analysis>"
        "</engine></engines>"
        "<aircraft><model uID='m'><reference><area>122.4</area></reference></model></aircraft>"
        "</vehicles></cpacs>"
    )
    inputs = read_from_cpacs(xml)
    assert inputs["bpr00"] == pytest.approx(5.9)


def test_cpacs_bypass_ratio_overrides_the_reference_value() -> None:
    """The adapter must forward the file's BPR00 into the model inputs.

    Checked at the source level because the run path needs a live OpenMDAO
    session; the intent is that a stated BPR is never silently replaced by
    the reference engine's.
    """
    import inspect

    from pycycle_mcp import cpacs_adapter

    src = inspect.getsource(cpacs_adapter)
    assert 'input_values["splitter.BPR"]' in src
    assert 'inputs.get("bpr00")' in src or 'inputs["bpr00"]' in src
