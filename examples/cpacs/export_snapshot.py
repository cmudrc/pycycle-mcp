"""Run deterministic pyCycle-style output and derivative snapshot logic."""

from __future__ import annotations

import json
from dataclasses import dataclass

from pycycle_mcp.session_manager import session_manager
from pycycle_mcp.tools import create_model, derivatives, execution, variables


@dataclass
class ExampleModel:
    """Model stand-in exposing the minimal list APIs."""

    name: str = "example-cycle"

    def list_inputs(
        self, prom_name: bool = True, out_stream: object | None = None
    ) -> list[tuple[str, dict[str, object]]]:
        del prom_name, out_stream
        return [("Mach", {"promoted_name": "Mach", "units": "", "desc": "Mach", "val": 0.8})]

    def list_outputs(
        self, prom_name: bool = True, out_stream: object | None = None
    ) -> list[tuple[str, dict[str, object]]]:
        del prom_name, out_stream
        return [
            (
                "Fn",
                {
                    "promoted_name": "Fn",
                    "units": "lbf",
                    "desc": "Net thrust",
                    "val": 5800.0,
                },
            )
        ]


class ExampleProblem:
    """Problem stand-in with deterministic output and derivative behavior."""

    def __init__(self) -> None:
        self.model = ExampleModel()
        self.values: dict[str, object] = {"Mach": 0.8, "Fn": 5800.0}
        self.iter_count = 0

    def set_val(self, name: str | None = None, value: object | None = None, **kwargs: object) -> None:
        if name is None:
            self.values.update(kwargs)
            return
        self.values[name] = value

    def get_val(self, name: str, units: str | None = None) -> object:
        del units
        return self.values[name]

    def set_solver_print(self, level: int = 0) -> None:
        del level

    def run_model(self) -> None:
        self.iter_count += 1
        mach = float(self.values.get("Mach", 0.8))
        self.values["Fn"] = round(5400.0 + (mach * 500.0), 3)

    def run_driver(self) -> None:
        self.run_model()

    def setup(self) -> None:
        return None

    def compute_totals(self, of: list[str], wrt: list[str]) -> dict[tuple[str, str], object]:
        return {(o, w): [[2.5]] for o in of for w in wrt}


def main() -> None:
    """Run deterministic tool flow and print a stable JSON snapshot."""
    session_id = session_manager.create_session(
        problem=ExampleProblem(),
        meta={"mode": "design", "options": {}},
    )

    variables.set_inputs({"session_id": session_id, "values": {"Mach": 0.9}})
    run_result = execution.run_cycle({"session_id": session_id, "outputs_of_interest": ["Fn"]})
    deriv_result = derivatives.compute_totals(
        {
            "session_id": session_id,
            "of": ["Fn"],
            "wrt": ["Mach"],
            "return_format": "by_pair",
        }
    )
    close_result = create_model.close_cycle_model({"session_id": session_id})

    payload = {
        "fn": run_result["outputs"]["Fn"],
        "jacobian_entry": deriv_result["jacobian"]["Fn"]["Mach"],
        "messages": run_result["messages"],
        "session_closed": close_result["success"],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
