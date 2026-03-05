"""Run a deterministic pyCycle session lifecycle and print JSON output."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from pycycle_mcp.session_manager import session_manager
from pycycle_mcp.tools import create_model, execution, variables


@dataclass
class ExampleModel:
    """Small model stand-in exposing list_inputs/list_outputs contracts."""

    name: str = "example-cycle"
    inputs: list[tuple[str, dict[str, object]]] = field(
        default_factory=lambda: [
            ("Mach", {"promoted_name": "Mach", "units": "", "desc": "Mach", "val": 0.8}),
            (
                "altitude_ft",
                {
                    "promoted_name": "altitude_ft",
                    "units": "ft",
                    "desc": "Altitude",
                    "val": 35000,
                },
            ),
        ]
    )
    outputs: list[tuple[str, dict[str, object]]] = field(
        default_factory=lambda: [("Fn", {"promoted_name": "Fn", "units": "lbf", "desc": "Net thrust", "val": 5900.0})]
    )

    def list_inputs(
        self, prom_name: bool = True, out_stream: object | None = None
    ) -> list[tuple[str, dict[str, object]]]:
        del prom_name, out_stream
        return self.inputs

    def list_outputs(
        self, prom_name: bool = True, out_stream: object | None = None
    ) -> list[tuple[str, dict[str, object]]]:
        del prom_name, out_stream
        return self.outputs


class ExampleProblem:
    """Small Problem stand-in compatible with pycycle_mcp tool expectations."""

    def __init__(self) -> None:
        self.model = ExampleModel()
        self.values: dict[str, object] = {"Fn": 5900.0, "Mach": 0.8}
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
        self.values["Fn"] = round(5000.0 + (mach * 1000.0), 3)

    def run_driver(self) -> None:
        self.run_model()

    def setup(self) -> None:
        return None

    def compute_totals(self, of: list[str], wrt: list[str]) -> dict[tuple[str, str], object]:
        return {(o, w): [[1.0]] for o in of for w in wrt}


def main() -> None:
    """Create, run, summarize, and close a deterministic session."""
    problem = ExampleProblem()
    session_id = session_manager.create_session(
        problem=problem,
        meta={"mode": "design", "options": {"Mach": 0.8}},
    )

    variables.set_inputs({"session_id": session_id, "values": {"Mach": 0.82}})
    run_result = execution.run_cycle({"session_id": session_id, "outputs_of_interest": ["Fn"]})
    summary = create_model.get_cycle_summary({"session_id": session_id})
    close_result = create_model.close_cycle_model({"session_id": session_id})

    payload = {
        "session_opened": True,
        "session_closed": close_result["success"],
        "mode": summary["mode"],
        "model_name": summary["model_name"],
        "output_names": sorted(run_result["outputs"].keys()),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
