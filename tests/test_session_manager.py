from __future__ import annotations

from pycycle_mcp_server.session_manager import SessionManager

from .conftest import DummyProblem


def test_session_lifecycle() -> None:
    manager = SessionManager()
    problem_obj = DummyProblem()
    session_id = manager.create_session(problem=problem_obj, meta={"mode": "design"})
    problem, meta = manager.get(session_id)

    assert problem is problem_obj
    assert meta["mode"] == "design"

    manager.close(session_id)
    try:
        manager.get(session_id)
    except KeyError:
        assert True
    else:  # pragma: no cover - safety
        raise AssertionError("Expected session to be removed")
