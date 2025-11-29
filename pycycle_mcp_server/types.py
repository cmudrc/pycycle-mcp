"""Shared typing protocol definitions for cycle problems."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class CycleModel(Protocol):
    name: str

    def list_inputs(
        self, prom_name: bool = True, out_stream: object | None = None
    ) -> list[tuple[str, dict[str, object]]]:  # pragma: no cover - protocol
        ...

    def list_outputs(
        self, prom_name: bool = True, out_stream: object | None = None
    ) -> list[tuple[str, dict[str, object]]]:  # pragma: no cover - protocol
        ...


@runtime_checkable
class CycleProblem(Protocol):
    model: CycleModel
    iter_count: int | None
    values: dict[str, object] | None

    def set_val(
        self, name: str | None = None, value: object | None = None, **kwargs: object
    ) -> None:  # pragma: no cover
        ...

    def get_val(
        self, name: str, units: str | None = None
    ) -> object:  # pragma: no cover
        ...

    def run_model(self) -> None:  # pragma: no cover
        ...

    def run_driver(self) -> None:  # pragma: no cover
        ...

    def setup(self) -> None:  # pragma: no cover
        ...

    def compute_totals(
        self, of: list[str], wrt: list[str]
    ) -> dict[tuple[str, str], object]:  # pragma: no cover
        ...
