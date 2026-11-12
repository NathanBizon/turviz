from pathlib import Path

import pytest

from turviz.engine import TapeSnapshot, run_machine, trace_metrics
from turviz.parser import ParseError, parse_tm, serialize_tm
from turviz.render import render_trace, state_colors


def test_parse_variable_halt_branch_and_comments() -> None:
    machine = parse_tm("""
        # writes one then returns
        A, 1, R, B, 0, L, B
        B, HALT, 1, R, A
    """)
    assert machine.initial_state == "A"
    assert machine.rules[1].on_zero is None
    assert machine.rules[1].on_one is not None


def test_parse_rejects_unknown_target() -> None:
    with pytest.raises(ParseError, match="état cible inconnu"):
        parse_tm("A,1,R,MISSING,HALT")


def test_engine_records_trace_and_halts() -> None:
    machine = parse_tm("A,1,R,B,HALT\nB,HALT,HALT")
    result = run_machine(machine, max_steps=10)
    assert result.halted
    assert result.snapshots[-1].cells == {0: 1}
    assert result.snapshots[-1].head == 1


def test_engine_respects_step_limit() -> None:
    machine = parse_tm("A,1,R,A,1,L,A")
    result = run_machine(machine, max_steps=2)
    assert not result.halted
    assert "limite" in result.reason
    assert len(result.snapshots) == 3


def test_engine_keeps_growing_tape_snapshots_compact() -> None:
    machine = parse_tm("A,1,R,A,1,R,A")
    result = run_machine(machine, max_steps=2_000)
    assert len(result.snapshots) == 2_001
    assert result.snapshots[-1].cells == {position: 1 for position in range(2_000)}


def test_engine_detects_repeated_configuration() -> None:
    machine = parse_tm("A,0,R,B,0,R,B\nB,0,L,A,0,L,A")
    result = run_machine(machine, max_steps=100)
    assert not result.halted
    assert result.cycle_start == 0
    assert result.cycle_length == 2
    assert "cycle détecté" in result.reason


def test_trace_metrics_describe_exploration() -> None:
    metrics = trace_metrics(
        (
            TapeSnapshot({}, 0, "A"),
            TapeSnapshot({0: 1, 2: 1}, 2, "B"),
        )
    )
    assert metrics.visited_positions == 3
    assert metrics.max_width == 3
    assert metrics.max_ones == 2
    assert metrics.final_ones == 2


def test_all_example_machines_parse() -> None:
    examples = Path(__file__).parents[1] / "examples"
    files = sorted(examples.glob("*.tm"))
    assert files
    for path in files:
        machine = parse_tm(path.read_text(encoding="utf-8"))
        assert machine.rules


def test_explicit_initial_state_is_backward_compatible() -> None:
    machine = parse_tm("""
        @version 1
        @initial B
        A,HALT,HALT
        B,0,R,A,1,L,A
    """)
    assert machine.initial_state == "B"
    assert serialize_tm(machine).startswith("@version 1\n@initial B\n")


def test_rejects_unknown_format_directive() -> None:
    with pytest.raises(ParseError, match="directive inconnue"):
        parse_tm("@future yes\nA,HALT,HALT")


def test_serialization_round_trip() -> None:
    source = "A,1,R,B,HALT\nB,HALT,0,L,A\n"
    assert serialize_tm(parse_tm(source)) == source


def test_head_color_changes_with_state() -> None:
    colors = state_colors(("A", "B"))
    image = render_trace(
        (
            TapeSnapshot({}, 0, "A"),
            TapeSnapshot({}, 0, "B"),
        ),
        state_color_map=colors,
    )
    first = image.pixelColor(20, 20)
    second = image.pixelColor(20, 44)
    assert first != second
    assert first.saturation() > 0
    assert second.saturation() > 0


def test_head_transparency_preserves_tape_value() -> None:
    colors = state_colors(("A",))
    image = render_trace(
        (
            TapeSnapshot({0: 1}, 0, "A"),
            TapeSnapshot({}, 0, "A"),
        ),
        state_color_map=colors,
    )
    one_under_head = image.pixelColor(20, 20)
    zero_under_head = image.pixelColor(20, 44)
    assert one_under_head != zero_under_head


def test_render_trace_bounds_large_traces() -> None:
    snapshots = tuple(TapeSnapshot({index: 1}, index, "A") for index in range(1_000))
    image = render_trace(snapshots, max_rows=10, max_columns=20)
    assert image.height() == 10 * 24 + 16
    assert image.width() <= 20 * 24 + 16
