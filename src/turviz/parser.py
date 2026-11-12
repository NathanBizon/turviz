from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from .model import Direction, StateRule, Symbol, Transition, TuringMachine


@dataclass
class ParseError(ValueError):
    line: int
    message: str
    column: int | None = None

    def __str__(self) -> str:
        location = f"line {self.line}"
        if self.column is not None:
            location += f", column {self.column}"
        return f"{location}: {self.message}"


def _transition(fields: list[str], line: int, branch: str) -> Transition | None:
    if not fields:
        raise ParseError(line, f"branche {branch} absente")
    if fields[0].upper() == "HALT":
        if len(fields) != 1:
            raise ParseError(line, f"a HALT {branch} branch must not contain extra fields")
        return None
    if len(fields) != 3:
        raise ParseError(line, f"branch {branch} must contain write, move and next state")
    if fields[0] not in {"0", "1"}:
        raise ParseError(line, f"invalid write value in branch {branch}: {fields[0]!r}")
    if fields[1].upper() not in {"L", "R"}:
        raise ParseError(line, f"invalid move in branch {branch}: {fields[1]!r}")
    if not fields[2]:
        raise ParseError(line, f"empty next state in branch {branch}")
    return Transition(
        cast(Symbol, int(fields[0])),
        cast(Direction, fields[1].upper()),
        fields[2],
    )


def parse_tm(text: str) -> TuringMachine:
    rules: list[StateRule] = []
    seen: set[str] = set()
    declared_initial: str | None = None
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        content = raw_line.split("#", 1)[0].strip()
        if not content:
            continue
        if content.startswith("@"):
            directive = content.split(None, 1)
            name = directive[0].lower()
            argument = directive[1].strip() if len(directive) == 2 else ""
            if name == "@version":
                if argument != "1":
                    raise ParseError(line_number, "unsupported format version; use @version 1")
            elif name == "@initial":
                if not argument:
                    raise ParseError(line_number, "@initial requires a state name")
                if declared_initial is not None:
                    raise ParseError(line_number, "@initial may only appear once")
                declared_initial = argument
            else:
                raise ParseError(line_number, f"unknown directive: {name}")
            continue
        fields = [field.strip() for field in content.split(",")]
        if len(fields) < 2:
            raise ParseError(line_number, "a line must contain a state and at least one branch")
        state = fields[0]
        if not state:
            raise ParseError(line_number, "empty state name")
        if state.upper() == "HALT":
            raise ParseError(line_number, "HALT is reserved for branches, not states")
        if state in seen:
            raise ParseError(line_number, f"duplicate state: {state}")
        seen.add(state)
        remaining = fields[1:]
        zero_fields = remaining[:1] if remaining and remaining[0].upper() == "HALT" else remaining[:3]
        one_fields = remaining[len(zero_fields):]
        zero = _transition(zero_fields, line_number, "0")
        one = _transition(one_fields, line_number, "1")
        rules.append(StateRule(state, zero, one))

    if not rules:
        raise ParseError(1, "the file contains no rules")
    initial_state = declared_initial or rules[0].name
    if initial_state not in seen:
        raise ParseError(1, f"unknown initial state: {initial_state}")
    machine = TuringMachine(tuple(rules), initial_state)
    for rule in rules:
        for transition in (rule.on_zero, rule.on_one):
            if transition and machine.rule_for(transition.next_state) is None:
                raise ParseError(1, f"unknown target state: {transition.next_state}")
    return machine


def serialize_tm(machine: TuringMachine) -> str:
    lines: list[str] = []
    if machine.initial_state != machine.rules[0].name:
        lines.append(f"@version 1")
        lines.append(f"@initial {machine.initial_state}")
    for rule in machine.rules:
        fields = [rule.name]
        for transition in (rule.on_zero, rule.on_one):
            if transition is None:
                fields.append("HALT")
            else:
                fields.extend((str(transition.write), transition.direction, transition.next_state))
        lines.append(",".join(fields))
    return "\n".join(lines) + "\n"
