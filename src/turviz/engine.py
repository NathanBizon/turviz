from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import blake2b
from typing import cast

from .model import Symbol, TuringMachine


@dataclass(frozen=True)
class TapeSnapshot:
    _tape: _Tape
    head: int
    state: str

    def __init__(
        self,
        cells: Mapping[int, int] | _Tape,
        head: int,
        state: str,
    ) -> None:
        object.__setattr__(
            self,
            "_tape",
            cells if isinstance(cells, _Tape) else _Tape.from_cells(cells),
        )
        object.__setattr__(self, "head", head)
        object.__setattr__(self, "state", state)

    @property
    def cells(self) -> dict[int, int]:
        return self._tape.materialize()


class _Tape:
    __slots__ = ("_cells", "parent", "position", "value")

    def __init__(
        self,
        parent: _Tape | None,
        position: int | None,
        value: int | None,
    ) -> None:
        self.parent = parent
        self.position = position
        self.value = value
        self._cells: dict[int, int] | None = None

    @classmethod
    def from_cells(cls, cells: Mapping[int, int]) -> _Tape:
        tape = cls(None, None, None)
        tape._cells = dict(cells)
        return tape

    def update(self, position: int, value: int | None) -> _Tape:
        return _Tape(self, position, value)

    def materialize(self) -> dict[int, int]:
        if self._cells is not None:
            return self._cells.copy()
        changes: list[tuple[int, int | None]] = []
        current: _Tape | None = self
        while current is not None and current._cells is None:
            assert current.position is not None
            changes.append((current.position, current.value))
            current = current.parent
        cells = current._cells.copy() if current is not None and current._cells else {}
        for position, value in reversed(changes):
            if value is None:
                cells.pop(position, None)
            else:
                cells[position] = value
        return cells.copy()


@dataclass(frozen=True)
class ExecutionResult:
    snapshots: tuple[TapeSnapshot, ...]
    halted: bool
    reason: str
    cycle_start: int | None = None
    cycle_length: int | None = None


@dataclass(frozen=True)
class TraceMetrics:
    visited_positions: int
    max_width: int
    max_ones: int
    final_ones: int


def trace_metrics(snapshots: tuple[TapeSnapshot, ...]) -> TraceMetrics:
    positions = {position for snapshot in snapshots for position in snapshot.cells}
    positions.update(snapshot.head for snapshot in snapshots)
    explored_width = max(positions) - min(positions) + 1 if positions else 1
    widths = [
        max(list(set(snapshot.cells) | {snapshot.head}))
        - min(list(set(snapshot.cells) | {snapshot.head}))
        + 1
        for snapshot in snapshots
    ]
    return TraceMetrics(
        visited_positions=explored_width,
        max_width=max(widths, default=1),
        max_ones=max((sum(snapshot.cells.values()) for snapshot in snapshots), default=0),
        final_ones=sum(snapshots[-1].cells.values()) if snapshots else 0,
    )


def run_machine(machine: TuringMachine, max_steps: int = 1_000) -> ExecutionResult:
    if max_steps < 0:
        raise ValueError("The step limit must be zero or greater")
    tape: dict[int, int] = {}
    tape_history = _Tape.from_cells(tape)
    tape_fingerprint = 0
    head = 0
    state = machine.initial_state
    snapshots = [TapeSnapshot({}, head, state)]
    rules = {rule.name: rule for rule in machine.rules}
    seen: dict[tuple[str, int, int], int] = {(state, head, tape_fingerprint): 0}
    for _ in range(max_steps):
        rule = rules.get(state)
        if rule is None:
            return ExecutionResult(tuple(snapshots), False, f"unknown state: {state}")
        symbol = cast(Symbol, tape.get(head, 0))
        transition = rule.transition_for(symbol)
        if transition is None:
            return ExecutionResult(tuple(snapshots), True, f"HALT on {state}, symbol {symbol}")
        if transition.write:
            if not tape.get(head):
                tape_fingerprint ^= _cell_fingerprint(head)
            tape[head] = 1
            tape_history = tape_history.update(head, 1)
        else:
            if tape.pop(head, None) is not None:
                tape_fingerprint ^= _cell_fingerprint(head)
                tape_history = tape_history.update(head, None)
        head += 1 if transition.direction == "R" else -1
        state = transition.next_state
        snapshot = TapeSnapshot(tape_history, head, state)
        snapshots.append(snapshot)
        configuration = (state, head, tape_fingerprint)
        if configuration in seen:
            cycle_start = seen[configuration]
            cycle_length = len(snapshots) - 1 - cycle_start
            return ExecutionResult(
                tuple(snapshots),
                False,
                f"cycle detected: steps {cycle_start} to {len(snapshots) - 1}",
                cycle_start,
                cycle_length,
            )
        seen[configuration] = len(snapshots) - 1
    return ExecutionResult(tuple(snapshots), False, f"step limit of {max_steps} reached")


def _cell_fingerprint(position: int) -> int:
    digest = blake2b(str(position).encode("ascii"), digest_size=16).digest()
    return int.from_bytes(digest, "big")
