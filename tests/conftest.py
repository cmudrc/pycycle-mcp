from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DummyModel:
    name: str = "dummy"
    inputs: list[tuple[str, dict[str, object]]] = field(default_factory=list)
    outputs: list[tuple[str, dict[str, object]]] = field(default_factory=list)

    def list_inputs(
        self, prom_name: bool = True, out_stream: object | None = None
    ) -> list[tuple[str, dict[str, object]]]:
        return self.inputs

    def list_outputs(
        self, prom_name: bool = True, out_stream: object | None = None
    ) -> list[tuple[str, dict[str, object]]]:
        return self.outputs


class DummyProblem:
    def __init__(self) -> None:
        self.model = DummyModel()
        self.values: dict[str, object] = {}
        self.iter_count = 0

    def set_val(
        self, name: str | None = None, value: object | None = None, **kwargs: object
    ) -> None:
        if name is None:
            for key, val in kwargs.items():
                self.values[key] = val
        else:
            self.values[str(name)] = value

    def get_val(self, name: str, units: str | None = None) -> object:
        if name not in self.values:
            raise KeyError(name)
        return self.values[name]

    def run_model(self) -> None:
        self.iter_count += 1

    def run_driver(self) -> None:
        self.iter_count += 1

    def compute_totals(self, of: list[str], wrt: list[str]) -> dict[tuple[str, str], object]:
        return {(o, w): [[1.0]] for o in of for w in wrt}
