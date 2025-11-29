from __future__ import annotations

from typing import cast

from pycycle_mcp_server.session_manager import session_manager
from pycycle_mcp_server.tools import derivatives, sweep

from .conftest import DummyProblem


def test_sweep_inputs_success() -> None:
    problem = DummyProblem()
    problem.model.inputs = [("Mach", {"promoted_name": "Mach"})]
    session_id = session_manager.create_session(
        problem=problem, meta={"mode": "design", "options": {}}
    )

    result = sweep.sweep_inputs(
        {
            "session_id": session_id,
            "sweep": [{"name": "Mach", "values": [0.7, 0.8]}],
            "outputs_of_interest": ["Fn"],
        }
    )

    results = cast(list[dict[str, object]], result["results"])
    assert len(results) == 2
    assert all(bool(entry["success"]) for entry in results)


def test_compute_totals_formats_by_pair() -> None:
    problem = DummyProblem()
    session_id = session_manager.create_session(
        problem=problem, meta={"mode": "design", "options": {}}
    )

    result = derivatives.compute_totals(
        {
            "session_id": session_id,
            "of": ["Fn"],
            "wrt": ["Mach"],
            "return_format": "by_pair",
        }
    )

    jacobian = cast(dict[str, dict[str, object]], result["jacobian"])
    assert "Fn" in jacobian
    assert jacobian["Fn"]["Mach"] == [[1.0]]
