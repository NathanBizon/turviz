from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Symbol = Literal[0, 1]
Direction = Literal["L", "R"]


@dataclass(frozen=True)
class Transition:
    write: Symbol
    direction: Direction
    next_state: str


@dataclass(frozen=True)
class StateRule:
    name: str
    on_zero: Transition | None
    on_one: Transition | None

    def transition_for(self, symbol: Symbol) -> Transition | None:
        return self.on_zero if symbol == 0 else self.on_one


@dataclass(frozen=True)
class TuringMachine:
    rules: tuple[StateRule, ...]
    initial_state: str

    def rule_for(self, state: str) -> StateRule | None:
        return next((rule for rule in self.rules if rule.name == state), None)
